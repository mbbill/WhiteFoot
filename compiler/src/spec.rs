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

/// Exact identity of `spec/kernel-spec-v0.12.md`.
pub const KERNEL_SPEC_V0_12_HASH: SpecHash = SpecHash::from_sha256([
    0xe2, 0xd5, 0x56, 0x63, 0x79, 0x89, 0x14, 0x54, 0xc0, 0x90, 0xe0, 0x37, 0xbd, 0x45, 0xc5, 0xf1,
    0xa8, 0xdf, 0x90, 0xba, 0x23, 0x50, 0x6a, 0x0f, 0x83, 0xce, 0x9a, 0xaa, 0x03, 0xb4, 0x14, 0x63,
]);

#[cfg(test)]
mod tests {
    use super::KERNEL_SPEC_V0_12_HASH;

    #[test]
    fn v0_12_identity_is_the_approved_candidate_identity() {
        assert_eq!(
            KERNEL_SPEC_V0_12_HASH.to_string(),
            "e2d5566379891454c090e037bd45c5f1a8df90ba23506a0f83ce9aaa03b41463"
        );
    }
}
