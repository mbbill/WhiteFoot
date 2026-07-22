//! Conservative textual LLVM emission for the first executable v0.11 family.
//!
//! Emission consumes only target-independent IR. It does not resolve names,
//! infer types, reconsider effects, or remove checks. Wrapping integer rows use
//! unflagged LLVM arithmetic; trapping rows use overflow intrinsics and explicit
//! aborting branches; explicit OP-5 checks are always retained.

use std::collections::{BTreeSet, HashMap};
use std::fmt::Write;

use crate::{
    IrConstant, IrFunction, IrInstruction, IrIntegerOperation, IrOperation, IrProgram,
    IrScalarType, IrTrapSite, IrValueId,
};

#[cfg(test)]
mod tests;

/// Trusted LLVM-emitter invariant failure, never a source verdict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BackendFailure {
    /// Target-independent IR was internally inconsistent.
    InvalidIr,
    /// An emitter identity or byte count overflowed.
    CounterOverflow,
    /// In-memory LLVM text formatting failed.
    TextEmission,
}

/// Complete deterministic textual LLVM module for the host toolchain.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LlvmModule {
    text: String,
}

impl LlvmModule {
    /// Consumes the module and returns its owned LLVM assembly.
    #[must_use]
    pub fn into_string(self) -> String {
        self.text
    }
}

/// Emits conservative LLVM assembly from one checked, target-independent IR.
pub fn emit_llvm_v0_11(program: &IrProgram<'_, '_, '_>) -> Result<LlvmModule, BackendFailure> {
    let mut traps = Vec::new();
    let mut intrinsics = BTreeSet::new();
    let mut functions = String::new();
    for function in program.functions() {
        let emitter =
            FunctionEmitter::new(program.functions(), function, &mut traps, &mut intrinsics);
        functions.push_str(&emitter.emit()?);
    }
    let main = program
        .functions()
        .get(program.main_ordinal() as usize)
        .ok_or(BackendFailure::InvalidIr)?;
    if main.result() != IrScalarType::Unit || !main.parameters().is_empty() {
        return Err(BackendFailure::InvalidIr);
    }

    let mut text = String::from(
        "; Whitefoot v0.11 conservative scalar module\nsource_filename = \"whitefoot\"\n\n",
    );
    for (index, bytes) in traps.iter().enumerate() {
        writeln!(
            text,
            "@.wf_trap.{index} = private unnamed_addr constant [{} x i8] c\"{}\", align 1",
            bytes.len(),
            llvm_bytes(bytes)
        )
        .map_err(|_| BackendFailure::TextEmission)?;
    }
    if !traps.is_empty() {
        text.push('\n');
        text.push_str("declare i64 @write(i32, ptr, i64)\n");
        text.push_str("declare void @abort() noreturn\n\n");
        text.push_str(
            "define private void @wf_trap(ptr %message, i64 %length) noreturn {\nentry:\n  br label %write.loop\nwrite.loop:\n  %cursor = phi ptr [ %message, %entry ], [ %next, %write.more ]\n  %remaining = phi i64 [ %length, %entry ], [ %left, %write.more ]\n  %written = call i64 @write(i32 2, ptr %cursor, i64 %remaining)\n  %complete = icmp eq i64 %written, %remaining\n  br i1 %complete, label %abort, label %write.incomplete\nwrite.incomplete:\n  %progress = icmp sgt i64 %written, 0\n  br i1 %progress, label %write.more, label %abort\nwrite.more:\n  %next = getelementptr i8, ptr %cursor, i64 %written\n  %left = sub i64 %remaining, %written\n  br label %write.loop\nabort:\n  call void @abort()\n  unreachable\n}\n\n",
        );
    }
    for intrinsic in intrinsics {
        let (name, ty) = intrinsic.split_once('|').ok_or(BackendFailure::InvalidIr)?;
        writeln!(text, "declare {{ {ty}, i1 }} @{name}({ty}, {ty})")
            .map_err(|_| BackendFailure::TextEmission)?;
    }
    if !functions.is_empty() {
        text.push('\n');
        text.push_str(&functions);
    }
    writeln!(
        text,
        "define i32 @main() {{\nentry:\n  %result = call i8 @{}()\n  ret i32 0\n}}",
        source_symbol(main.name())
    )
    .map_err(|_| BackendFailure::TextEmission)?;
    Ok(LlvmModule { text })
}

struct FunctionEmitter<'functions, 'state> {
    functions: &'functions [IrFunction],
    function: &'functions IrFunction,
    traps: &'state mut Vec<Vec<u8>>,
    intrinsics: &'state mut BTreeSet<String>,
    operands: HashMap<IrValueId, String>,
    output: String,
    temporary: u32,
    control: u32,
}

impl<'functions, 'state> FunctionEmitter<'functions, 'state> {
    fn new(
        functions: &'functions [IrFunction],
        function: &'functions IrFunction,
        traps: &'state mut Vec<Vec<u8>>,
        intrinsics: &'state mut BTreeSet<String>,
    ) -> Self {
        Self {
            functions,
            function,
            traps,
            intrinsics,
            operands: HashMap::new(),
            output: String::new(),
            temporary: 0,
            control: 0,
        }
    }

    fn emit(mut self) -> Result<String, BackendFailure> {
        write!(
            self.output,
            "define {} @{}(",
            llvm_type(self.function.result())?,
            source_symbol(self.function.name())
        )
        .map_err(|_| BackendFailure::TextEmission)?;
        for (index, (value, ty)) in self.function.parameters().iter().enumerate() {
            if index != 0 {
                self.output.push_str(", ");
            }
            let name = format!("%v{}", value.ordinal());
            write!(self.output, "{} {name}", llvm_type(*ty)?)
                .map_err(|_| BackendFailure::TextEmission)?;
            self.operands.insert(*value, name);
        }
        self.output.push_str(") {\nentry:\n");
        for instruction in self.function.instructions() {
            self.emit_instruction(instruction)?;
        }
        self.output.push_str("}\n\n");
        Ok(self.output)
    }

    fn emit_instruction(&mut self, instruction: &IrInstruction) -> Result<(), BackendFailure> {
        match instruction {
            IrInstruction::Define {
                result,
                ty,
                operation,
            } => self.emit_definition(*result, *ty, operation),
            IrInstruction::Check { condition, trap } => {
                let condition = self.value(*condition)?.to_owned();
                let control = self.next_control()?;
                let trap_id = self.register_trap(trap)?;
                writeln!(
                    self.output,
                    "  br i1 {condition}, label %check.cont.{control}, label %check.trap.{control}\ncheck.trap.{control}:\n  call void @wf_trap(ptr @.wf_trap.{trap_id}, i64 {})\n  unreachable\ncheck.cont.{control}:",
                    self.traps[trap_id].len()
                )
                .map_err(|_| BackendFailure::TextEmission)
            }
            IrInstruction::Return(value) => {
                let ty = self
                    .function
                    .value_type(*value)
                    .ok_or(BackendFailure::InvalidIr)?;
                let value = self.value(*value)?.to_owned();
                writeln!(self.output, "  ret {} {value}", llvm_type(ty)?)
                    .map_err(|_| BackendFailure::TextEmission)
            }
        }
    }

    fn emit_definition(
        &mut self,
        result: IrValueId,
        ty: IrScalarType,
        operation: &IrOperation,
    ) -> Result<(), BackendFailure> {
        if self.operands.contains_key(&result) || self.function.value_type(result) != Some(ty) {
            return Err(BackendFailure::InvalidIr);
        }
        let operand = match operation {
            IrOperation::Constant(constant) => constant_operand(*constant, ty)?,
            IrOperation::Call {
                function,
                arguments,
            } => self.emit_call(result, ty, *function, arguments)?,
            IrOperation::Integer {
                operation,
                operand_type,
                arguments,
                trap,
            } => self.emit_integer(
                result,
                ty,
                *operation,
                *operand_type,
                *arguments,
                trap.as_ref(),
            )?,
        };
        self.operands.insert(result, operand);
        Ok(())
    }

    fn emit_call(
        &mut self,
        result: IrValueId,
        ty: IrScalarType,
        function: u32,
        arguments: &[IrValueId],
    ) -> Result<String, BackendFailure> {
        let target = self
            .functions
            .get(function as usize)
            .ok_or(BackendFailure::InvalidIr)?;
        if target.result() != ty || target.parameters().len() != arguments.len() {
            return Err(BackendFailure::InvalidIr);
        }
        let mut rendered = Vec::with_capacity(arguments.len());
        for (argument, (_, parameter_type)) in arguments.iter().zip(target.parameters()) {
            if self.function.value_type(*argument) != Some(*parameter_type) {
                return Err(BackendFailure::InvalidIr);
            }
            rendered.push(format!(
                "{} {}",
                llvm_type(*parameter_type)?,
                self.value(*argument)?
            ));
        }
        let joined = rendered.join(", ");
        let name = format!("%v{}", result.ordinal());
        writeln!(
            self.output,
            "  {name} = call {} @{}({joined})",
            llvm_type(ty)?,
            source_symbol(target.name())
        )
        .map_err(|_| BackendFailure::TextEmission)?;
        Ok(name)
    }

    #[allow(clippy::too_many_arguments)]
    fn emit_integer(
        &mut self,
        result: IrValueId,
        result_type: IrScalarType,
        operation: IrIntegerOperation,
        operand_type: IrScalarType,
        arguments: [IrValueId; 2],
        trap: Option<&IrTrapSite>,
    ) -> Result<String, BackendFailure> {
        let IrScalarType::Integer { width, signed } = operand_type else {
            return Err(BackendFailure::InvalidIr);
        };
        if arguments
            .iter()
            .any(|argument| self.function.value_type(*argument) != Some(operand_type))
        {
            return Err(BackendFailure::InvalidIr);
        }
        let ty = llvm_type(operand_type)?;
        let left = self.value(arguments[0])?.to_owned();
        let right = self.value(arguments[1])?.to_owned();
        let result_name = format!("%v{}", result.ordinal());
        match operation {
            IrIntegerOperation::AddWrap
            | IrIntegerOperation::SubtractWrap
            | IrIntegerOperation::MultiplyWrap => {
                if result_type != operand_type || trap.is_some() {
                    return Err(BackendFailure::InvalidIr);
                }
                let opcode = match operation {
                    IrIntegerOperation::AddWrap => "add",
                    IrIntegerOperation::SubtractWrap => "sub",
                    IrIntegerOperation::MultiplyWrap => "mul",
                    _ => return Err(BackendFailure::InvalidIr),
                };
                writeln!(
                    self.output,
                    "  {result_name} = {opcode} {ty} {left}, {right}"
                )
                .map_err(|_| BackendFailure::TextEmission)?;
            }
            IrIntegerOperation::AddTrap
            | IrIntegerOperation::SubtractTrap
            | IrIntegerOperation::MultiplyTrap => {
                if result_type != operand_type {
                    return Err(BackendFailure::InvalidIr);
                }
                let trap = trap.ok_or(BackendFailure::InvalidIr)?;
                let stem = match operation {
                    IrIntegerOperation::AddTrap => "add",
                    IrIntegerOperation::SubtractTrap => "sub",
                    IrIntegerOperation::MultiplyTrap => "mul",
                    _ => return Err(BackendFailure::InvalidIr),
                };
                let sign = if signed { 's' } else { 'u' };
                let intrinsic = format!("llvm.{sign}{stem}.with.overflow.i{width}");
                self.intrinsics.insert(format!("{intrinsic}|{ty}"));
                let temporary = self.next_temporary()?;
                let overflow = self.next_temporary()?;
                let control = self.next_control()?;
                let trap_id = self.register_trap(trap)?;
                writeln!(
                    self.output,
                    "  %{temporary} = call {{ {ty}, i1 }} @{intrinsic}({ty} {left}, {ty} {right})\n  {result_name} = extractvalue {{ {ty}, i1 }} %{temporary}, 0\n  %{overflow} = extractvalue {{ {ty}, i1 }} %{temporary}, 1\n  br i1 %{overflow}, label %overflow.trap.{control}, label %overflow.cont.{control}\noverflow.trap.{control}:\n  call void @wf_trap(ptr @.wf_trap.{trap_id}, i64 {})\n  unreachable\noverflow.cont.{control}:",
                    self.traps[trap_id].len()
                )
                .map_err(|_| BackendFailure::TextEmission)?;
            }
            IrIntegerOperation::Equal
            | IrIntegerOperation::NotEqual
            | IrIntegerOperation::Less
            | IrIntegerOperation::LessEqual
            | IrIntegerOperation::Greater
            | IrIntegerOperation::GreaterEqual => {
                if result_type != IrScalarType::Bool || trap.is_some() {
                    return Err(BackendFailure::InvalidIr);
                }
                let predicate = match operation {
                    IrIntegerOperation::Equal => "eq",
                    IrIntegerOperation::NotEqual => "ne",
                    IrIntegerOperation::Less if signed => "slt",
                    IrIntegerOperation::Less => "ult",
                    IrIntegerOperation::LessEqual if signed => "sle",
                    IrIntegerOperation::LessEqual => "ule",
                    IrIntegerOperation::Greater if signed => "sgt",
                    IrIntegerOperation::Greater => "ugt",
                    IrIntegerOperation::GreaterEqual if signed => "sge",
                    IrIntegerOperation::GreaterEqual => "uge",
                    _ => return Err(BackendFailure::InvalidIr),
                };
                writeln!(
                    self.output,
                    "  {result_name} = icmp {predicate} {ty} {left}, {right}"
                )
                .map_err(|_| BackendFailure::TextEmission)?;
            }
        }
        Ok(result_name)
    }

    fn value(&self, value: IrValueId) -> Result<&str, BackendFailure> {
        self.operands
            .get(&value)
            .map(String::as_str)
            .ok_or(BackendFailure::InvalidIr)
    }

    fn register_trap(&mut self, trap: &IrTrapSite) -> Result<usize, BackendFailure> {
        let index = self.traps.len();
        let _ = u32::try_from(index).map_err(|_| BackendFailure::CounterOverflow)?;
        self.traps.push(trap_record(trap));
        Ok(index)
    }

    fn next_temporary(&mut self) -> Result<String, BackendFailure> {
        let current = self.temporary;
        self.temporary = self
            .temporary
            .checked_add(1)
            .ok_or(BackendFailure::CounterOverflow)?;
        Ok(format!("t{current}"))
    }

    fn next_control(&mut self) -> Result<u32, BackendFailure> {
        let current = self.control;
        self.control = self
            .control
            .checked_add(1)
            .ok_or(BackendFailure::CounterOverflow)?;
        Ok(current)
    }
}

fn llvm_type(ty: IrScalarType) -> Result<&'static str, BackendFailure> {
    match ty {
        IrScalarType::Unit => Ok("i8"),
        IrScalarType::Bool => Ok("i1"),
        IrScalarType::Integer { width: 8, .. } => Ok("i8"),
        IrScalarType::Integer { width: 16, .. } => Ok("i16"),
        IrScalarType::Integer { width: 32, .. } => Ok("i32"),
        IrScalarType::Integer { width: 64, .. } => Ok("i64"),
        IrScalarType::Integer { .. } => Err(BackendFailure::InvalidIr),
    }
}

fn constant_operand(constant: IrConstant, ty: IrScalarType) -> Result<String, BackendFailure> {
    match (constant, ty) {
        (IrConstant::Unit, IrScalarType::Unit) => Ok("0".to_owned()),
        (IrConstant::Bool(value), IrScalarType::Bool) => Ok(u8::from(value).to_string()),
        (
            IrConstant::Integer {
                ty: constant_ty,
                bits,
            },
            actual_ty,
        ) if constant_ty == actual_ty => {
            let IrScalarType::Integer { width, signed } = actual_ty else {
                return Err(BackendFailure::InvalidIr);
            };
            let mask = if width == 64 {
                u64::MAX
            } else {
                (1_u64 << width) - 1
            };
            let bits = bits & mask;
            let rendered = if signed && bits & (1_u64 << (width - 1)) != 0 {
                (i128::from(bits) - (1_i128 << width)).to_string()
            } else {
                bits.to_string()
            };
            Ok(rendered)
        }
        _ => Err(BackendFailure::InvalidIr),
    }
}

fn source_symbol(name: &str) -> String {
    format!("wf_{name}")
}

fn trap_record(trap: &IrTrapSite) -> Vec<u8> {
    let components = trap
        .node_path
        .iter()
        .map(u32::to_string)
        .collect::<Vec<_>>()
        .join(",");
    format!(
        "{{\"rule_id\":{},\"message\":{},\"function\":{},\"node_path\":[{components}]}}\n",
        json_string(trap.rule_id),
        json_string(&trap.message),
        json_string(&trap.function)
    )
    .into_bytes()
}

fn json_string(value: &str) -> String {
    let mut encoded = String::from("\"");
    for byte in value.bytes() {
        match byte {
            b'"' => encoded.push_str("\\\""),
            b'\\' => encoded.push_str("\\\\"),
            b'\n' => encoded.push_str("\\n"),
            _ => encoded.push(char::from(byte)),
        }
    }
    encoded.push('"');
    encoded
}

fn llvm_bytes(bytes: &[u8]) -> String {
    let mut encoded = String::with_capacity(bytes.len() * 3);
    for byte in bytes {
        let _ = write!(encoded, "\\{byte:02X}");
    }
    encoded
}
