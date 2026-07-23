use core::fmt;

/// The SHA-256 identity of one immutable numbered kernel specification.
#[derive(Clone, Copy, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct SpecHash([u8; 32]);

impl SpecHash {
    /// Create an identity from its exact SHA-256 bytes.
    #[must_use]
    pub const fn from_sha256(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    /// Return the exact SHA-256 bytes.
    #[must_use]
    pub const fn as_bytes(self) -> [u8; 32] {
        self.0
    }
}

impl fmt::Debug for SpecHash {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(self, formatter)
    }
}

impl fmt::Display for SpecHash {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        for byte in self.0 {
            write!(formatter, "{byte:02x}")?;
        }
        Ok(())
    }
}

/// Exact identity of `spec/kernel-spec-v0.13.md`.
pub const KERNEL_SPEC_V0_13_HASH: SpecHash = SpecHash::from_sha256([
    0xed, 0x93, 0xcc, 0x43, 0xa6, 0xa2, 0x24, 0x72, 0x5f, 0x81, 0x3b, 0x1a, 0xdf, 0xc4, 0xc1, 0x9f,
    0xbb, 0x64, 0xdc, 0x5a, 0xb2, 0x94, 0xb2, 0x5d, 0x92, 0x43, 0x92, 0xd2, 0x95, 0x9b, 0x77, 0xcd,
]);

#[cfg(test)]
mod tests {
    use super::KERNEL_SPEC_V0_13_HASH;

    #[test]
    fn v0_13_identity_is_the_approved_candidate_identity() {
        assert_eq!(
            KERNEL_SPEC_V0_13_HASH.to_string(),
            "ed93cc43a6a224725f813b1adfc4c19fbb64dc5ab294b25d924392d2959b77cd"
        );
    }
}
