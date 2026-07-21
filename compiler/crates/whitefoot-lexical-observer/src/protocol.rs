use std::io::Read;

use whitefoot_contract::SourceLimits;
use whitefoot_frontend::LexLimits;

const REQUEST_MAGIC: [u8; 8] = *b"WFLEXREQ";
const REQUEST_VERSION: u16 = 1;
const FIXED_REQUEST_BYTES: usize = 98;

const HARD_MAX_SOURCES: u32 = 4_096;
const HARD_MAX_LOGICAL_PATH_BYTES: u64 = 4_096;
const HARD_MAX_SOURCE_BYTES: u64 = 1_048_576;
const HARD_MAX_TOTAL_SOURCE_BYTES: u64 = 1_048_576;
const HARD_MAX_BINDING_BYTES: u64 = 2_097_152;

pub(crate) const RESPONSE_MAGIC: [u8; 8] = *b"WFLEXRSP";
pub(crate) const RESPONSE_VERSION: u16 = 1;
pub(crate) const HARD_MAX_RESPONSE_BYTES: u64 = 33_554_432;

pub(crate) struct Request {
    pub(crate) source_limits: SourceLimits,
    pub(crate) lex_limits: LexLimits,
    pub(crate) binding: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum AdapterError {
    RequestRead,
    RequestMagic,
    RequestVersion,
    SourceLimitsOutsideProfile,
    BindingLengthOutsideProfile,
    BindingLengthOutsideHost,
    RequestStorageUnavailable,
    TrailingRequestBytes,
    BindingInvalid,
    SpecificationMismatch,
    SourceBundleInvalid,
    SourceBindingDisagreement,
    ProjectionInvariant,
    ResponseLimitExceeded,
    ResponseStorageUnavailable,
    OutputWrite,
}

impl AdapterError {
    pub(crate) const fn code(self) -> &'static str {
        match self {
            Self::RequestRead => "request-read-failed",
            Self::RequestMagic => "request-magic-invalid",
            Self::RequestVersion => "request-version-unsupported",
            Self::SourceLimitsOutsideProfile => "source-limits-outside-observer-profile",
            Self::BindingLengthOutsideProfile => "binding-length-outside-observer-profile",
            Self::BindingLengthOutsideHost => "binding-length-outside-host-domain",
            Self::RequestStorageUnavailable => "request-storage-unavailable",
            Self::TrailingRequestBytes => "request-has-trailing-bytes",
            Self::BindingInvalid => "source-binding-invalid",
            Self::SpecificationMismatch => "specification-mismatch",
            Self::SourceBundleInvalid => "source-bundle-invalid",
            Self::SourceBindingDisagreement => "source-binding-reconstruction-disagrees",
            Self::ProjectionInvariant => "lexical-projection-invariant-failed",
            Self::ResponseLimitExceeded => "observation-response-limit-exceeded",
            Self::ResponseStorageUnavailable => "observation-response-storage-unavailable",
            Self::OutputWrite => "observation-output-write-failed",
        }
    }
}

pub(crate) fn read_request(input: &mut impl Read) -> Result<Request, AdapterError> {
    let mut header = [0_u8; FIXED_REQUEST_BYTES];
    input
        .read_exact(&mut header)
        .map_err(|_| AdapterError::RequestRead)?;
    let mut reader = HeaderReader::new(&header);
    if reader.take::<8>() != REQUEST_MAGIC {
        return Err(AdapterError::RequestMagic);
    }
    if reader.u16() != REQUEST_VERSION {
        return Err(AdapterError::RequestVersion);
    }

    let source_limits = SourceLimits {
        max_sources: reader.u32(),
        max_logical_path_bytes: reader.u64(),
        max_source_bytes: reader.u64(),
        max_total_source_bytes: reader.u64(),
        max_binding_bytes: reader.u64(),
    };
    check_source_profile(source_limits)?;
    let lex_limits = LexLimits {
        max_sources: reader.u32(),
        max_source_bytes: reader.u64(),
        max_total_source_bytes: reader.u64(),
        max_token_bytes: reader.u64(),
        max_tokens: reader.u64(),
        max_lexemes: reader.u64(),
    };
    let binding_length = reader.u64();
    if binding_length > source_limits.max_binding_bytes || binding_length > HARD_MAX_BINDING_BYTES {
        return Err(AdapterError::BindingLengthOutsideProfile);
    }
    let host_length =
        usize::try_from(binding_length).map_err(|_| AdapterError::BindingLengthOutsideHost)?;
    let mut binding = Vec::new();
    binding
        .try_reserve_exact(host_length)
        .map_err(|_| AdapterError::RequestStorageUnavailable)?;
    binding.resize(host_length, 0);
    input
        .read_exact(&mut binding)
        .map_err(|_| AdapterError::RequestRead)?;

    let mut trailing = [0_u8; 1];
    match input.read(&mut trailing) {
        Ok(0) => {}
        Ok(_) => return Err(AdapterError::TrailingRequestBytes),
        Err(_) => return Err(AdapterError::RequestRead),
    }
    Ok(Request {
        source_limits,
        lex_limits,
        binding,
    })
}

fn check_source_profile(limits: SourceLimits) -> Result<(), AdapterError> {
    if limits.max_sources > HARD_MAX_SOURCES
        || limits.max_logical_path_bytes > HARD_MAX_LOGICAL_PATH_BYTES
        || limits.max_source_bytes > HARD_MAX_SOURCE_BYTES
        || limits.max_total_source_bytes > HARD_MAX_TOTAL_SOURCE_BYTES
        || limits.max_binding_bytes > HARD_MAX_BINDING_BYTES
    {
        return Err(AdapterError::SourceLimitsOutsideProfile);
    }
    Ok(())
}

struct HeaderReader<'bytes> {
    bytes: &'bytes [u8],
    cursor: usize,
}

impl<'bytes> HeaderReader<'bytes> {
    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    fn take<const LENGTH: usize>(&mut self) -> [u8; LENGTH] {
        let mut result = [0_u8; LENGTH];
        let end = self.cursor + LENGTH;
        result.copy_from_slice(&self.bytes[self.cursor..end]);
        self.cursor = end;
        result
    }

    fn u16(&mut self) -> u16 {
        u16::from_be_bytes(self.take())
    }

    fn u32(&mut self) -> u32 {
        u32::from_be_bytes(self.take())
    }

    fn u64(&mut self) -> u64 {
        u64::from_be_bytes(self.take())
    }
}

pub(crate) struct ResponseEncoder {
    bytes: Vec<u8>,
    expected_length: u64,
}

impl ResponseEncoder {
    pub(crate) fn with_capacity(expected_length: u64) -> Result<Self, AdapterError> {
        if expected_length > HARD_MAX_RESPONSE_BYTES {
            return Err(AdapterError::ResponseLimitExceeded);
        }
        let host_length =
            usize::try_from(expected_length).map_err(|_| AdapterError::ResponseLimitExceeded)?;
        let mut bytes = Vec::new();
        bytes
            .try_reserve_exact(host_length)
            .map_err(|_| AdapterError::ResponseStorageUnavailable)?;
        Ok(Self {
            bytes,
            expected_length,
        })
    }

    pub(crate) fn bytes(mut self, value: &[u8]) -> Result<Self, AdapterError> {
        let old_length =
            u64::try_from(self.bytes.len()).map_err(|_| AdapterError::ResponseLimitExceeded)?;
        let added = u64::try_from(value.len()).map_err(|_| AdapterError::ResponseLimitExceeded)?;
        let new_length = old_length
            .checked_add(added)
            .ok_or(AdapterError::ResponseLimitExceeded)?;
        if new_length > self.expected_length {
            return Err(AdapterError::ProjectionInvariant);
        }
        self.bytes.extend_from_slice(value);
        Ok(self)
    }

    pub(crate) fn u8(self, value: u8) -> Result<Self, AdapterError> {
        self.bytes(&[value])
    }

    pub(crate) fn u16(self, value: u16) -> Result<Self, AdapterError> {
        self.bytes(&value.to_be_bytes())
    }

    pub(crate) fn u32(self, value: u32) -> Result<Self, AdapterError> {
        self.bytes(&value.to_be_bytes())
    }

    pub(crate) fn u64(self, value: u64) -> Result<Self, AdapterError> {
        self.bytes(&value.to_be_bytes())
    }

    pub(crate) fn finish(self) -> Result<Vec<u8>, AdapterError> {
        let actual =
            u64::try_from(self.bytes.len()).map_err(|_| AdapterError::ProjectionInvariant)?;
        if actual != self.expected_length {
            return Err(AdapterError::ProjectionInvariant);
        }
        Ok(self.bytes)
    }
}
