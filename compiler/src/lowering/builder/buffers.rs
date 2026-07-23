use crate::semantic::{
    CheckedBufferRoot, CheckedBufferSetTarget, CheckedExpression, CheckedFlatElement, TrapSite,
};

use super::*;

impl IrBuilder<'_> {
    pub(super) fn lower_buffer_fill(
        &mut self,
        element: CheckedFlatElement,
        length: &CheckedExpression,
        value: &CheckedExpression,
        trap: &TrapSite,
    ) -> Result<IrValueId, LoweringFailure> {
        let element = lower_flat_element(element);
        let length = self.expression(length)?;
        let value = self.expression(value)?;
        if self.value_type(length)?
            != (IrType::Integer {
                width: 64,
                signed: false,
            })
            || self.value_type(value)? != element.ty()
        {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        self.define(
            IrType::Buffer { element },
            IrOperation::BufferFill {
                length,
                value,
                trap: trap.clone().into(),
            },
        )
    }

    pub(super) fn lower_buffer_length(
        &mut self,
        root: CheckedBufferRoot,
    ) -> Result<IrValueId, LoweringFailure> {
        let buffer = self.buffer_root(root)?;
        self.define(
            IrType::Integer {
                width: 64,
                signed: false,
            },
            IrOperation::BufferLength { buffer },
        )
    }

    pub(super) fn lower_buffer_index(
        &mut self,
        root: CheckedBufferRoot,
        offset: &CheckedExpression,
        trap: &TrapSite,
    ) -> Result<IrValueId, LoweringFailure> {
        let buffer = self.buffer_root(root)?;
        let IrType::Buffer { element } = self.value_type(buffer)? else {
            return Err(LoweringFailure::InvalidCheckedProgram);
        };
        let offset = self.expression(offset)?;
        if self.value_type(offset)?
            != (IrType::Integer {
                width: 64,
                signed: false,
            })
        {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        self.define(
            element.ty(),
            IrOperation::BufferIndex {
                buffer,
                offset,
                trap: trap.clone().into(),
            },
        )
    }

    pub(super) fn lower_buffer_set(
        &mut self,
        root: IrValueId,
        target: &CheckedBufferSetTarget,
        value: &CheckedExpression,
    ) -> Result<IrValueId, LoweringFailure> {
        let element = lower_flat_element(target.root.element);
        if self.value_type(root)? != (IrType::Buffer { element }) {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        let offset = self.expression(&target.offset)?;
        if self.value_type(offset)?
            != (IrType::Integer {
                width: 64,
                signed: false,
            })
        {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        let index = self.define(
            IrType::GuardedBufferIndex { element },
            IrOperation::BufferBoundsCheck {
                buffer: root,
                offset,
                trap: target.trap.clone().into(),
            },
        )?;
        let value = self.expression(value)?;
        if self.value_type(value)? != element.ty() {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        self.current_block_mut()?
            .instructions
            .push(IrInstruction::StoreBuffer {
                buffer: root,
                index,
                value,
            });
        Ok(root)
    }

    fn buffer_root(&self, root: CheckedBufferRoot) -> Result<IrValueId, LoweringFailure> {
        let value = self
            .bindings
            .get(&root.binding)
            .copied()
            .ok_or(LoweringFailure::InvalidCheckedProgram)?;
        if self.value_type(value)?
            != (IrType::Buffer {
                element: lower_flat_element(root.element),
            })
        {
            return Err(LoweringFailure::InvalidCheckedProgram);
        }
        Ok(value)
    }
}
