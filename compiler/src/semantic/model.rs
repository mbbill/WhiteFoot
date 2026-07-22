use crate::{DeclarationId, NodePath};

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct FunctionId(pub(crate) u32);

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct BindingId(pub(crate) u32);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum IntegerType {
    I8,
    I16,
    I32,
    I64,
    U8,
    U16,
    U32,
    U64,
}

impl IntegerType {
    pub(crate) const fn width(self) -> u8 {
        match self {
            Self::I8 | Self::U8 => 8,
            Self::I16 | Self::U16 => 16,
            Self::I32 | Self::U32 => 32,
            Self::I64 | Self::U64 => 64,
        }
    }

    pub(crate) const fn signed(self) -> bool {
        matches!(self, Self::I8 | Self::I16 | Self::I32 | Self::I64)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CheckedType {
    Unit,
    Bool,
    Integer(IntegerType),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CheckedValue {
    Unit,
    Bool(bool),
    Integer { ty: IntegerType, bits: u64 },
}

impl CheckedValue {
    pub(crate) const fn ty(self) -> CheckedType {
        match self {
            Self::Unit => CheckedType::Unit,
            Self::Bool(_) => CheckedType::Bool,
            Self::Integer { ty, .. } => CheckedType::Integer(ty),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CheckedIntegerOperation {
    AddWrap,
    SubtractWrap,
    MultiplyWrap,
    AddTrap,
    SubtractTrap,
    MultiplyTrap,
    Equal,
    NotEqual,
    Less,
    LessEqual,
    Greater,
    GreaterEqual,
}

impl CheckedIntegerOperation {
    pub(crate) const fn traps(self) -> bool {
        matches!(
            self,
            Self::AddTrap | Self::SubtractTrap | Self::MultiplyTrap
        )
    }

    pub(crate) const fn result_type(self, operand: IntegerType) -> CheckedType {
        match self {
            Self::Equal
            | Self::NotEqual
            | Self::Less
            | Self::LessEqual
            | Self::Greater
            | Self::GreaterEqual => CheckedType::Bool,
            _ => CheckedType::Integer(operand),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TrapSite {
    pub(crate) rule_id: &'static str,
    pub(crate) message: String,
    pub(crate) function: String,
    pub(crate) node_path: NodePath,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CheckedExpression {
    Constant(CheckedValue),
    Binding {
        binding: BindingId,
        ty: CheckedType,
    },
    UserCall {
        function: FunctionId,
        arguments: Vec<CheckedExpression>,
        result: CheckedType,
    },
    IntegerOperation {
        operation: CheckedIntegerOperation,
        operand_type: IntegerType,
        arguments: Vec<CheckedExpression>,
        trap: Option<TrapSite>,
    },
}

impl CheckedExpression {
    pub(crate) const fn ty(&self) -> CheckedType {
        match self {
            Self::Constant(value) => value.ty(),
            Self::Binding { ty, .. } | Self::UserCall { result: ty, .. } => *ty,
            Self::IntegerOperation {
                operation,
                operand_type,
                ..
            } => operation.result_type(*operand_type),
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum CheckedStatement {
    Let {
        binding: BindingId,
        value: CheckedExpression,
    },
    Evaluate(CheckedExpression),
    Check {
        condition: CheckedExpression,
        trap: TrapSite,
    },
    Return(CheckedExpression),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CheckedParameter {
    pub(crate) name: String,
    pub(crate) binding: BindingId,
    pub(crate) ty: CheckedType,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct CheckedFunction {
    pub(crate) id: FunctionId,
    pub(crate) declaration: DeclarationId,
    pub(crate) name: String,
    pub(crate) parameters: Vec<CheckedParameter>,
    pub(crate) result: CheckedType,
    pub(crate) declared_traps: bool,
    pub(crate) body: Vec<CheckedStatement>,
}

#[derive(Debug)]
pub(crate) struct CheckedProgramData {
    pub(crate) functions: Vec<CheckedFunction>,
    pub(crate) main: FunctionId,
}
