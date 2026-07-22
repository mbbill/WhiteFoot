//! Target-independent lowering from semantically checked Whitefoot v0.11.
//!
//! The IR is intentionally small and private in spirit: it records explicit
//! scalar values, direct calls, retained checks, and returns. It contains no
//! source admission logic and grants no authority to reconstruct semantic
//! decisions.

use std::collections::HashMap;

use crate::CheckedProgram;
use crate::semantic::{
    BindingId, CheckedExpression, CheckedIntegerOperation, CheckedProgramData, CheckedStatement,
    CheckedType, CheckedValue, TrapSite,
};

/// Dense identity of one target-independent scalar value.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub struct IrValueId(u32);

impl IrValueId {
    /// Returns the dense function-local value ordinal.
    #[must_use]
    pub const fn ordinal(self) -> u32 {
        self.0
    }

    const fn index(self) -> usize {
        self.0 as usize
    }
}

/// One already-checked scalar type in the first executable IR family.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IrScalarType {
    /// The sole unit value.
    Unit,
    /// Prelude `Bool`.
    Bool,
    /// One exact integer primitive.
    Integer {
        /// Bit width: 8, 16, 32, or 64.
        width: u8,
        /// Whether comparisons and overflow use signed semantics.
        signed: bool,
    },
}

impl From<CheckedType> for IrScalarType {
    fn from(value: CheckedType) -> Self {
        match value {
            CheckedType::Unit => Self::Unit,
            CheckedType::Bool => Self::Bool,
            CheckedType::Integer(integer) => Self::Integer {
                width: integer.width(),
                signed: integer.signed(),
            },
        }
    }
}

/// One explicit target-independent operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IrOperation {
    /// A fully checked scalar constant.
    Constant(IrConstant),
    /// A direct source-function call.
    Call {
        /// Dense checked function target.
        function: u32,
        /// Arguments in declared parameter order.
        arguments: Vec<IrValueId>,
    },
    /// One exact OP-2 integer row.
    Integer {
        /// Selected operation.
        operation: IrIntegerOperation,
        /// Exact operand integer type.
        operand_type: IrScalarType,
        /// Two checked operands.
        arguments: [IrValueId; 2],
        /// Retained overflow trap for `.trap`, absent for total rows.
        trap: Option<IrTrapSite>,
    },
}

/// One exact scalar constant value.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IrConstant {
    /// Unit.
    Unit,
    /// Prelude `Bool` discriminant.
    Bool(bool),
    /// Exact two's-complement or unsigned bits.
    Integer {
        /// Exact integer type.
        ty: IrScalarType,
        /// Low `width` bits of the value.
        bits: u64,
    },
}

/// Integer rows currently represented by the IR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IrIntegerOperation {
    /// Modular addition.
    AddWrap,
    /// Modular subtraction.
    SubtractWrap,
    /// Modular multiplication.
    MultiplyWrap,
    /// Checked addition that traps on overflow.
    AddTrap,
    /// Checked subtraction that traps on overflow.
    SubtractTrap,
    /// Checked multiplication that traps on overflow.
    MultiplyTrap,
    /// Equality.
    Equal,
    /// Inequality.
    NotEqual,
    /// Signed- or unsigned-less-than selected by the operand type.
    Less,
    /// Signed- or unsigned-less-than-or-equal.
    LessEqual,
    /// Signed- or unsigned-greater-than.
    Greater,
    /// Signed- or unsigned-greater-than-or-equal.
    GreaterEqual,
}

impl From<CheckedIntegerOperation> for IrIntegerOperation {
    fn from(value: CheckedIntegerOperation) -> Self {
        match value {
            CheckedIntegerOperation::AddWrap => Self::AddWrap,
            CheckedIntegerOperation::SubtractWrap => Self::SubtractWrap,
            CheckedIntegerOperation::MultiplyWrap => Self::MultiplyWrap,
            CheckedIntegerOperation::AddTrap => Self::AddTrap,
            CheckedIntegerOperation::SubtractTrap => Self::SubtractTrap,
            CheckedIntegerOperation::MultiplyTrap => Self::MultiplyTrap,
            CheckedIntegerOperation::Equal => Self::Equal,
            CheckedIntegerOperation::NotEqual => Self::NotEqual,
            CheckedIntegerOperation::Less => Self::Less,
            CheckedIntegerOperation::LessEqual => Self::LessEqual,
            CheckedIntegerOperation::Greater => Self::Greater,
            CheckedIntegerOperation::GreaterEqual => Self::GreaterEqual,
        }
    }
}

/// Runtime trap data fixed by DIAG-3 before target lowering.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IrTrapSite {
    pub(crate) rule_id: &'static str,
    pub(crate) message: String,
    pub(crate) function: String,
    pub(crate) node_path: Vec<u32>,
}

impl From<TrapSite> for IrTrapSite {
    fn from(value: TrapSite) -> Self {
        Self {
            rule_id: value.rule_id,
            message: value.message,
            function: value.function,
            node_path: value.node_path.components().to_vec(),
        }
    }
}

/// One instruction in source evaluation order.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum IrInstruction {
    /// Define one value with an exact checked type.
    Define {
        /// New dense value identity.
        result: IrValueId,
        /// Exact result type.
        ty: IrScalarType,
        /// Operation producing the value.
        operation: IrOperation,
    },
    /// Retained explicit OP-5 check.
    Check {
        /// Checked `Bool` condition.
        condition: IrValueId,
        /// Exact required trap record data.
        trap: IrTrapSite,
    },
    /// Explicit source return, including unit.
    Return(IrValueId),
}

/// One completely lowered source function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IrFunction {
    name: String,
    parameters: Vec<(IrValueId, IrScalarType)>,
    result: IrScalarType,
    values: Vec<IrScalarType>,
    instructions: Vec<IrInstruction>,
}

impl IrFunction {
    /// Returns the source function name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Returns the exact checked result type.
    #[must_use]
    pub const fn result(&self) -> IrScalarType {
        self.result
    }

    /// Returns parameters in declared order.
    #[must_use]
    pub fn parameters(&self) -> &[(IrValueId, IrScalarType)] {
        &self.parameters
    }

    /// Returns instructions in source evaluation order.
    #[must_use]
    pub fn instructions(&self) -> &[IrInstruction] {
        &self.instructions
    }

    pub(crate) fn value_type(&self, value: IrValueId) -> Option<IrScalarType> {
        self.values.get(value.index()).copied()
    }
}

/// Target-independent IR retaining its exact checked-program authority.
#[derive(Debug)]
pub struct IrProgram<'classified, 'lexed, 'source> {
    _checked: CheckedProgram<'classified, 'lexed, 'source>,
    functions: Vec<IrFunction>,
    main: u32,
}

impl IrProgram<'_, '_, '_> {
    /// Returns every source function in checked dense order.
    #[must_use]
    pub fn functions(&self) -> &[IrFunction] {
        &self.functions
    }

    /// Returns the checked entry-function ordinal.
    #[must_use]
    pub const fn main_ordinal(&self) -> u32 {
        self.main
    }
}

/// Trusted lowering invariant failure, never a source verdict.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LoweringFailure {
    /// A checked dense identity was missing or duplicated.
    InvalidCheckedProgram,
    /// A dense IR identity overflowed.
    CounterOverflow,
}

/// Lowers one complete checked program into explicit target-independent IR.
pub fn lower_checked_v0_11<'classified, 'lexed, 'source>(
    checked: CheckedProgram<'classified, 'lexed, 'source>,
) -> Result<IrProgram<'classified, 'lexed, 'source>, LoweringFailure> {
    let functions = lower_program_data(&checked.data)?;
    Ok(IrProgram {
        main: checked.data.main.0,
        _checked: checked,
        functions,
    })
}

fn lower_program_data(data: &CheckedProgramData) -> Result<Vec<IrFunction>, LoweringFailure> {
    data.functions.iter().map(lower_function).collect()
}

fn lower_function(
    function: &crate::semantic::CheckedFunction,
) -> Result<IrFunction, LoweringFailure> {
    let mut builder = IrBuilder::default();
    for parameter in &function.parameters {
        let value = builder.new_value(parameter.ty.into())?;
        builder.bindings.insert(parameter.binding, value);
        builder.parameters.push((value, parameter.ty.into()));
    }
    for statement in &function.body {
        match statement {
            CheckedStatement::Let { binding, value } => {
                let value = builder.expression(value)?;
                if builder.bindings.insert(*binding, value).is_some() {
                    return Err(LoweringFailure::InvalidCheckedProgram);
                }
            }
            CheckedStatement::Evaluate(expression) => {
                builder.expression(expression)?;
            }
            CheckedStatement::Check { condition, trap } => {
                let condition = builder.expression(condition)?;
                builder.instructions.push(IrInstruction::Check {
                    condition,
                    trap: trap.clone().into(),
                });
            }
            CheckedStatement::Return(expression) => {
                let value = builder.expression(expression)?;
                builder.instructions.push(IrInstruction::Return(value));
            }
        }
    }
    Ok(IrFunction {
        name: function.name.clone(),
        parameters: builder.parameters,
        result: function.result.into(),
        values: builder.values,
        instructions: builder.instructions,
    })
}

#[derive(Default)]
struct IrBuilder {
    bindings: HashMap<BindingId, IrValueId>,
    parameters: Vec<(IrValueId, IrScalarType)>,
    values: Vec<IrScalarType>,
    instructions: Vec<IrInstruction>,
}

impl IrBuilder {
    fn new_value(&mut self, ty: IrScalarType) -> Result<IrValueId, LoweringFailure> {
        let id = IrValueId(
            u32::try_from(self.values.len()).map_err(|_| LoweringFailure::CounterOverflow)?,
        );
        self.values.push(ty);
        Ok(id)
    }

    fn expression(&mut self, expression: &CheckedExpression) -> Result<IrValueId, LoweringFailure> {
        match expression {
            CheckedExpression::Binding { binding, .. } => self
                .bindings
                .get(binding)
                .copied()
                .ok_or(LoweringFailure::InvalidCheckedProgram),
            CheckedExpression::Constant(value) => {
                let ty: IrScalarType = value.ty().into();
                let constant = match value {
                    CheckedValue::Unit => IrConstant::Unit,
                    CheckedValue::Bool(value) => IrConstant::Bool(*value),
                    CheckedValue::Integer { ty, bits } => IrConstant::Integer {
                        ty: CheckedType::Integer(*ty).into(),
                        bits: *bits,
                    },
                };
                self.define(ty, IrOperation::Constant(constant))
            }
            CheckedExpression::UserCall {
                function,
                arguments,
                result,
            } => {
                let arguments = arguments
                    .iter()
                    .map(|argument| self.expression(argument))
                    .collect::<Result<Vec<_>, _>>()?;
                self.define(
                    (*result).into(),
                    IrOperation::Call {
                        function: function.0,
                        arguments,
                    },
                )
            }
            CheckedExpression::IntegerOperation {
                operation,
                operand_type,
                arguments,
                trap,
            } => {
                let [left, right] = arguments.as_slice() else {
                    return Err(LoweringFailure::InvalidCheckedProgram);
                };
                let left = self.expression(left)?;
                let right = self.expression(right)?;
                self.define(
                    expression.ty().into(),
                    IrOperation::Integer {
                        operation: (*operation).into(),
                        operand_type: CheckedType::Integer(*operand_type).into(),
                        arguments: [left, right],
                        trap: trap.clone().map(Into::into),
                    },
                )
            }
        }
    }

    fn define(
        &mut self,
        ty: IrScalarType,
        operation: IrOperation,
    ) -> Result<IrValueId, LoweringFailure> {
        let result = self.new_value(ty)?;
        self.instructions.push(IrInstruction::Define {
            result,
            ty,
            operation,
        });
        Ok(result)
    }
}
