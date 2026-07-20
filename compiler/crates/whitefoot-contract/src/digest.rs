use core::fmt;

/// A raw SHA-256 value.
///
/// The type represents already computed bytes; hashing is deliberately not
/// implemented until the workspace admits a reviewed cryptographic dependency.
#[derive(Clone, Copy, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct Sha256Digest([u8; 32]);

impl Sha256Digest {
    /// Creates a digest from its exact 32-byte representation.
    #[must_use]
    pub const fn from_bytes(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    /// Returns the exact digest bytes.
    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

impl fmt::Debug for Sha256Digest {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(self, formatter)
    }
}

impl fmt::Display for Sha256Digest {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        for byte in self.0 {
            write!(formatter, "{byte:02x}")?;
        }
        Ok(())
    }
}

/// The SHA-256 identity of one immutable numbered kernel specification.
#[derive(Clone, Copy, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub struct SpecHash(Sha256Digest);

impl SpecHash {
    /// Creates a specification identity from a previously computed SHA-256.
    #[must_use]
    pub const fn from_sha256(bytes: [u8; 32]) -> Self {
        Self(Sha256Digest::from_bytes(bytes))
    }

    /// Returns the domain-neutral SHA-256 value.
    #[must_use]
    pub const fn digest(self) -> Sha256Digest {
        self.0
    }
}

impl fmt::Display for SpecHash {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        fmt::Display::fmt(&self.0, formatter)
    }
}

/// Exact identity of `spec/kernel-spec-v0.8.md`.
pub const KERNEL_SPEC_V0_8_HASH: SpecHash = SpecHash::from_sha256([
    0xd0, 0x43, 0x36, 0xf7, 0xfa, 0x8d, 0x1a, 0x6a, 0x0f, 0x03, 0xfe, 0x58, 0xa1, 0x7f, 0x97, 0x2b,
    0x65, 0x82, 0x17, 0xa7, 0x3a, 0x3d, 0xff, 0x91, 0xa9, 0x06, 0xb4, 0xba, 0x29, 0x53, 0x28, 0xa8,
]);

#[cfg(test)]
mod tests {
    use super::KERNEL_SPEC_V0_8_HASH;

    #[test]
    fn v0_8_hash_matches_workspace_lock() {
        let locked = include_str!("../../../kernel-spec-v0.8.sha256").trim_end_matches('\n');
        assert_eq!(KERNEL_SPEC_V0_8_HASH.to_string(), locked);
    }
}
