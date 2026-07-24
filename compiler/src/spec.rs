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

/// Version label of the active immutable kernel specification.
pub const ACTIVE_KERNEL_SPEC_VERSION: &str = "v0.17";

/// Repository-relative path of the active immutable kernel specification.
pub const ACTIVE_KERNEL_SPEC_PATH: &str = "spec/kernel-spec-v0.17.md";

/// Exact UTF-8 text of the active immutable kernel specification.
pub const ACTIVE_KERNEL_SPEC_TEXT: &str = include_str!("../../spec/kernel-spec-v0.17.md");

/// Exact bytes of the active immutable kernel specification.
pub const ACTIVE_KERNEL_SPEC_BYTES: &[u8] = ACTIVE_KERNEL_SPEC_TEXT.as_bytes();

/// SHA-256 identity of the active immutable kernel specification.
pub const ACTIVE_KERNEL_SPEC_HASH: SpecHash = SpecHash::from_sha256([
    0x19, 0x64, 0x2f, 0xfb, 0x0a, 0xd9, 0xc7, 0x14, 0x6a, 0x84, 0x76, 0x2a, 0xda, 0x19, 0x2e, 0xd2,
    0xa2, 0x5d, 0xc4, 0x46, 0xa9, 0x3c, 0x4d, 0x06, 0x0a, 0xa2, 0x9d, 0x9a, 0x99, 0xf6, 0x9c, 0x93,
]);

#[cfg(test)]
mod tests {
    use super::{
        ACTIVE_KERNEL_SPEC_BYTES, ACTIVE_KERNEL_SPEC_HASH, ACTIVE_KERNEL_SPEC_PATH,
        ACTIVE_KERNEL_SPEC_TEXT, ACTIVE_KERNEL_SPEC_VERSION,
    };

    #[test]
    fn active_spec_identity_is_the_approved_candidate_identity() {
        assert_eq!(ACTIVE_KERNEL_SPEC_VERSION, "v0.17");
        assert_eq!(ACTIVE_KERNEL_SPEC_PATH, "spec/kernel-spec-v0.17.md");
        assert_eq!(ACTIVE_KERNEL_SPEC_BYTES, ACTIVE_KERNEL_SPEC_TEXT.as_bytes());
        assert_eq!(
            ACTIVE_KERNEL_SPEC_HASH.to_string(),
            "19642ffb0ad9c7146a84762ada192ed2a25dc446a93c4d060aa29d9a99f69c93"
        );
    }
}
