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

/// Exact identity of `spec/kernel-spec-v0.11.md`.
pub const KERNEL_SPEC_V0_11_HASH: SpecHash = SpecHash::from_sha256([
    0x05, 0x0e, 0x11, 0x0c, 0x8c, 0x5e, 0xb3, 0x14, 0x3c, 0x9d, 0x3f, 0x54, 0x96, 0x8a, 0x9d, 0xf9,
    0x12, 0x5f, 0x1d, 0x4b, 0x59, 0x91, 0xf5, 0x27, 0xb8, 0xa1, 0x59, 0x38, 0xa4, 0x29, 0x2f, 0xbc,
]);

#[cfg(test)]
mod tests {
    use super::KERNEL_SPEC_V0_11_HASH;

    #[test]
    fn v0_11_identity_is_the_approved_candidate_identity() {
        assert_eq!(
            KERNEL_SPEC_V0_11_HASH.to_string(),
            "050e110c8c5eb3143c9d3f54968a9df9125f1d4b5991f527b8a15938a4292fbc"
        );
    }
}
