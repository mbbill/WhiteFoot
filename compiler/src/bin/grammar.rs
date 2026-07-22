#![forbid(unsafe_code)]

use std::fmt;
use std::path::Path;

use whitefoot::{
    ALL_FIXED_TERMINALS_V0_10, ALL_TERMINAL_PREDICATES_V0_10, GrammarNodeKindV0_10,
    KERNEL_SPEC_V0_10_HASH, LexLimits, LexOutcome, Lexeme, LookaheadPredicateV0_10, ParseLimits,
    ParseOutcome, ProductionV0_10, SourceBundle, SourceInput, SourceLimits, TerminalLimits,
    TerminalOutcome, TerminalPredicateV0_10, TokenKind, classify_terminals_v0_10,
    diagnostic_terminal_order_v0_10, grammar_node_v0_10, lex_v0_10, parse_v0_10, productions_v0_10,
};

const ACTIVE_SPEC: &[u8] = include_bytes!("../../../spec/kernel-spec-v0.10.md");
const PARSER_PROBE: &[u8] = b"fn main() -> own unit pure {\n  return unit;\n}\n";
const PROPAGATE_PROBE: &[u8] =
    b"fn main() -> own unit pure {\n  let value: own unit = propagate unit;\n  return value;\n}\n";
const TRANSLATED_PROPAGATE_PROBE: &[u8] =
    b"fn main() -> own unit pure {\n  let value: own unit = try unit;\n  return value;\n}\n";

const FRONTEND_SECTIONS: [(&str, &str); 3] = [
    ("[FORM-1]", "## 4. Types"),
    ("[CONST-1]", "## 5. Ownership"),
    ("[EFF-1]", "[EFF-2]"),
];

#[derive(Debug)]
enum VerifyError {
    Invocation(&'static str),
    Read(std::io::Error),
    NonUtf8,
    MissingSection(&'static str),
    ChangedFrontendContract,
    InvalidRename(&'static str),
    InvalidCompilerGrammar(&'static str),
    ParserProbe(String),
}

impl fmt::Display for VerifyError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Invocation(message) => formatter.write_str(message),
            Self::Read(error) => write!(formatter, "cannot read candidate: {error}"),
            Self::NonUtf8 => formatter.write_str("candidate is not UTF-8"),
            Self::MissingSection(marker) => {
                write!(formatter, "candidate is missing frontend section {marker}")
            }
            Self::ChangedFrontendContract => formatter.write_str(
                "candidate changes the lexer or source grammar beyond the supported one-for-one Result-propagation rename",
            ),
            Self::InvalidRename(message) => {
                write!(formatter, "invalid Result-propagation grammar rename: {message}")
            }
            Self::InvalidCompilerGrammar(message) => {
                write!(formatter, "active compiler grammar is inconsistent: {message}")
            }
            Self::ParserProbe(message) => {
                write!(formatter, "active compiler parser probe failed: {message}")
            }
        }
    }
}

impl std::error::Error for VerifyError {}

fn main() {
    if let Err(error) = run() {
        eprintln!("whitefoot-grammar: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), VerifyError> {
    let mut arguments = std::env::args_os();
    let _program = arguments.next();
    let candidate = arguments.next().ok_or(VerifyError::Invocation(
        "usage: whitefoot-grammar PATH-TO-CANDIDATE",
    ))?;
    if arguments.next().is_some() {
        return Err(VerifyError::Invocation(
            "usage: whitefoot-grammar PATH-TO-CANDIDATE",
        ));
    }
    let bytes = std::fs::read(Path::new(&candidate)).map_err(VerifyError::Read)?;
    let report = verify_candidate(&bytes)?;
    let kind = match report.contract {
        ContractKind::Exact => "grammar-preserving",
        ContractKind::ResultPropagationRename => "grammar-isomorphic Result-propagation rename",
    };
    println!(
        "{kind} candidate verified by the active compiler: {} productions, {} decisions, {} terminal predicates",
        report.productions, report.decisions, report.terminals,
    );
    Ok(())
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ContractKind {
    Exact,
    ResultPropagationRename,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct VerifyReport {
    contract: ContractKind,
    productions: usize,
    decisions: usize,
    terminals: usize,
}

fn verify_candidate(candidate: &[u8]) -> Result<VerifyReport, VerifyError> {
    let active_contract = frontend_contract(ACTIVE_SPEC)?;
    let candidate_contract = frontend_contract(candidate)?;
    let contract = if candidate_contract == active_contract {
        ContractKind::Exact
    } else {
        verify_result_propagation_rename(&active_contract, &candidate_contract)?;
        ContractKind::ResultPropagationRename
    };
    let mut report = verify_compiler_grammar()?;
    report.contract = contract;
    match contract {
        ContractKind::Exact => run_parser_probe(PARSER_PROBE)?,
        ContractKind::ResultPropagationRename => {
            verify_translated_result_propagation_tables()?;
            run_candidate_lexer_probe()?;
            run_parser_probe(TRANSLATED_PROPAGATE_PROBE)?;
        }
    }
    Ok(report)
}

fn frontend_contract(specification: &[u8]) -> Result<Vec<&str>, VerifyError> {
    let text = std::str::from_utf8(specification).map_err(|_| VerifyError::NonUtf8)?;
    let mut contract = Vec::new();
    for (start_marker, end_marker) in FRONTEND_SECTIONS {
        let start =
            line_start(text, start_marker).ok_or(VerifyError::MissingSection(start_marker))?;
        let end = line_start(&text[start..], end_marker)
            .map(|offset| start + offset)
            .ok_or(VerifyError::MissingSection(end_marker))?;
        let section = text
            .get(start..end)
            .ok_or(VerifyError::InvalidCompilerGrammar(
                "frontend section bounds are invalid",
            ))?;
        contract.push(section);
    }
    Ok(contract)
}

fn verify_result_propagation_rename(
    active: &[&str],
    candidate: &[&str],
) -> Result<(), VerifyError> {
    const OLD_PRODUCTION: &str = "try_let_rhs";
    const NEW_PRODUCTION: &str = "propagate_let_rhs";
    const OLD_TERMINAL: &str = "\"try\"";
    const NEW_TERMINAL: &str = "\"propagate\"";

    if active.len() != candidate.len() {
        return Err(VerifyError::ChangedFrontendContract);
    }
    let active_productions = occurrence_count(active, OLD_PRODUCTION);
    let active_terminals = occurrence_count(active, OLD_TERMINAL);
    if active_productions == 0 || active_terminals != 1 {
        return Err(VerifyError::InvalidCompilerGrammar(
            "active Result-propagation spelling is not uniquely identifiable",
        ));
    }
    if occurrence_count(active, NEW_PRODUCTION) != 0 || occurrence_count(active, NEW_TERMINAL) != 0
    {
        return Err(VerifyError::InvalidCompilerGrammar(
            "active frontend already contains the proposed spelling",
        ));
    }
    if occurrence_count(candidate, NEW_PRODUCTION) == 0
        && occurrence_count(candidate, NEW_TERMINAL) == 0
    {
        return Err(VerifyError::ChangedFrontendContract);
    }
    if occurrence_count(candidate, OLD_PRODUCTION) != 0
        || occurrence_count(candidate, OLD_TERMINAL) != 0
    {
        return Err(VerifyError::InvalidRename(
            "the old fixed terminal or production remains in the candidate frontend",
        ));
    }
    if occurrence_count(candidate, NEW_PRODUCTION) != active_productions
        || occurrence_count(candidate, NEW_TERMINAL) != active_terminals
    {
        return Err(VerifyError::InvalidRename(
            "the replacement endpoints do not have the active contract's exact multiplicity",
        ));
    }

    let normalized: Vec<String> = candidate
        .iter()
        .map(|section| {
            section
                .replace(NEW_PRODUCTION, OLD_PRODUCTION)
                .replace(NEW_TERMINAL, OLD_TERMINAL)
        })
        .collect();
    if normalized
        .iter()
        .map(String::as_str)
        .ne(active.iter().copied())
    {
        return Err(VerifyError::ChangedFrontendContract);
    }
    Ok(())
}

fn occurrence_count(sections: &[&str], needle: &str) -> usize {
    sections
        .iter()
        .map(|section| section.match_indices(needle).count())
        .sum()
}

fn line_start(text: &str, marker: &str) -> Option<usize> {
    text.match_indices(marker)
        .map(|(index, _)| index)
        .find(|index| *index == 0 || text.as_bytes().get(index - 1) == Some(&b'\n'))
}

fn verify_translated_result_propagation_tables() -> Result<(), VerifyError> {
    use whitefoot::FixedTerminalV0_10;

    for (left_index, left) in ALL_FIXED_TERMINALS_V0_10.iter().enumerate() {
        for right in &ALL_FIXED_TERMINALS_V0_10[left_index + 1..] {
            if candidate_fixed_spelling(*left) == candidate_fixed_spelling(*right) {
                return Err(VerifyError::InvalidRename(
                    "the translated fixed-terminal inventory is not unique",
                ));
            }
        }
    }
    if candidate_fixed_terminal(b"propagate") != Some(FixedTerminalV0_10::Try)
        || candidate_fixed_terminal(b"try").is_some()
        || candidate_identifier(b"propagate")
        || !candidate_identifier(b"try")
    {
        return Err(VerifyError::InvalidRename(
            "the translated IDENT and fixed-terminal partition is incorrect",
        ));
    }
    if productions_v0_10()
        .iter()
        .filter(|production| **production == ProductionV0_10::TryLetRhs)
        .count()
        != 1
        || !production_contains_fixed(ProductionV0_10::TryLetRhs, FixedTerminalV0_10::Try)?
    {
        return Err(VerifyError::InvalidCompilerGrammar(
            "the active propagation production is not uniquely mapped to its fixed terminal",
        ));
    }
    Ok(())
}

fn candidate_fixed_spelling(terminal: whitefoot::FixedTerminalV0_10) -> &'static [u8] {
    if terminal == whitefoot::FixedTerminalV0_10::Try {
        b"propagate"
    } else {
        terminal.spelling()
    }
}

fn candidate_fixed_terminal(spelling: &[u8]) -> Option<whitefoot::FixedTerminalV0_10> {
    ALL_FIXED_TERMINALS_V0_10
        .iter()
        .copied()
        .find(|terminal| candidate_fixed_spelling(*terminal) == spelling)
}

fn candidate_identifier(spelling: &[u8]) -> bool {
    let Some((first, rest)) = spelling.split_first() else {
        return false;
    };
    first.is_ascii_lowercase()
        && rest
            .iter()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || *byte == b'_')
        && candidate_fixed_terminal(spelling).is_none()
}

fn production_contains_fixed(
    production: ProductionV0_10,
    terminal: whitefoot::FixedTerminalV0_10,
) -> Result<bool, VerifyError> {
    let mut stack = vec![production.root()];
    while let Some(node_id) = stack.pop() {
        let node = grammar_node_v0_10(node_id).ok_or(VerifyError::InvalidCompilerGrammar(
            "a production references a missing node",
        ))?;
        if node
            .terminals()
            .contains(&LookaheadPredicateV0_10::Terminal(
                TerminalPredicateV0_10::Fixed(terminal),
            ))
        {
            return Ok(true);
        }
        stack.extend_from_slice(node.children());
    }
    Ok(false)
}

fn verify_compiler_grammar() -> Result<VerifyReport, VerifyError> {
    for (left_index, left) in ALL_FIXED_TERMINALS_V0_10.iter().enumerate() {
        for right in &ALL_FIXED_TERMINALS_V0_10[left_index + 1..] {
            if left.spelling() == right.spelling() {
                return Err(VerifyError::InvalidCompilerGrammar(
                    "two fixed terminals have the same spelling",
                ));
            }
        }
    }

    let order = diagnostic_terminal_order_v0_10();
    if order.len() != ALL_TERMINAL_PREDICATES_V0_10.len() {
        return Err(VerifyError::InvalidCompilerGrammar(
            "terminal inventory and diagnostic order differ",
        ));
    }
    for predicate in ALL_TERMINAL_PREDICATES_V0_10 {
        if order
            .iter()
            .filter(|candidate| **candidate == LookaheadPredicateV0_10::Terminal(predicate))
            .count()
            != 1
        {
            return Err(VerifyError::InvalidCompilerGrammar(
                "terminal diagnostic order is not a permutation",
            ));
        }
    }

    let mut decisions = 0_usize;
    for production in productions_v0_10() {
        let mut stack = vec![production.root()];
        while let Some(node_id) = stack.pop() {
            let node = grammar_node_v0_10(node_id).ok_or(VerifyError::InvalidCompilerGrammar(
                "a production references a missing node",
            ))?;
            if let Some(decision) = node.decision() {
                decisions = decisions
                    .checked_add(1)
                    .ok_or(VerifyError::InvalidCompilerGrammar(
                        "decision count overflowed",
                    ))?;
                let mut covered = vec![false; usize::from(decision.arm_count())];
                for row in decision.rows() {
                    let arm = covered.get_mut(usize::from(row.arm())).ok_or(
                        VerifyError::InvalidCompilerGrammar("a SELECT row has an invalid arm"),
                    )?;
                    *arm = true;
                    if row.position(0).is_none() || row.position(1).is_none() {
                        return Err(VerifyError::InvalidCompilerGrammar(
                            "a SELECT row does not have two positions",
                        ));
                    }
                }
                if covered.iter().any(|covered| !covered) {
                    return Err(VerifyError::InvalidCompilerGrammar(
                        "a decision arm has no SELECT row",
                    ));
                }
                verify_disjoint_rows(decision.rows())?;
            }
            if matches!(
                node.kind(),
                GrammarNodeKindV0_10::Sequence
                    | GrammarNodeKindV0_10::Choice
                    | GrammarNodeKindV0_10::Group
                    | GrammarNodeKindV0_10::Optional
                    | GrammarNodeKindV0_10::RepeatZero
                    | GrammarNodeKindV0_10::RepeatOne
            ) {
                stack.extend_from_slice(node.children());
            }
        }
    }
    Ok(VerifyReport {
        contract: ContractKind::Exact,
        productions: productions_v0_10().len(),
        decisions,
        terminals: order.len(),
    })
}

fn verify_disjoint_rows(rows: &[whitefoot::SelectRowV0_10]) -> Result<(), VerifyError> {
    for (left_index, left) in rows.iter().enumerate() {
        for right in &rows[left_index + 1..] {
            if left.arm() == right.arm() {
                continue;
            }
            let first_overlaps = predicates_overlap(
                left.position(0)
                    .ok_or(VerifyError::InvalidCompilerGrammar(
                        "a SELECT row is missing position zero",
                    ))?
                    .predicate(),
                right
                    .position(0)
                    .ok_or(VerifyError::InvalidCompilerGrammar(
                        "a SELECT row is missing position zero",
                    ))?
                    .predicate(),
            );
            let second_overlaps = predicates_overlap(
                left.position(1)
                    .ok_or(VerifyError::InvalidCompilerGrammar(
                        "a SELECT row is missing position one",
                    ))?
                    .predicate(),
                right
                    .position(1)
                    .ok_or(VerifyError::InvalidCompilerGrammar(
                        "a SELECT row is missing position one",
                    ))?
                    .predicate(),
            );
            if first_overlaps && second_overlaps {
                return Err(VerifyError::InvalidCompilerGrammar(
                    "two source arms have overlapping SELECT_2 rows",
                ));
            }
        }
    }
    Ok(())
}

fn predicates_overlap(left: LookaheadPredicateV0_10, right: LookaheadPredicateV0_10) -> bool {
    if left == right {
        return true;
    }
    matches!(
        (left, right),
        (
            LookaheadPredicateV0_10::Terminal(TerminalPredicateV0_10::Fixed(
                whitefoot::FixedTerminalV0_10::Unit
            )),
            LookaheadPredicateV0_10::Terminal(TerminalPredicateV0_10::Literal)
        ) | (
            LookaheadPredicateV0_10::Terminal(TerminalPredicateV0_10::Literal),
            LookaheadPredicateV0_10::Terminal(TerminalPredicateV0_10::Fixed(
                whitefoot::FixedTerminalV0_10::Unit
            ))
        )
    )
}

fn run_candidate_lexer_probe() -> Result<(), VerifyError> {
    let bundle = parser_probe_bundle(PROPAGATE_PROBE)?;
    let lexed = match lex_v0_10(&bundle, parser_probe_lex_limits()) {
        LexOutcome::Complete(lexed) => lexed,
        outcome => return Err(VerifyError::ParserProbe(format!("lexing: {outcome:?}"))),
    };
    let mut found = false;
    for (source, _) in bundle.iter() {
        let Some(lexemes) = lexed.source_lexemes(source) else {
            return Err(VerifyError::ParserProbe(
                "candidate lexer probe lost a source partition".to_owned(),
            ));
        };
        for lexeme in lexemes {
            let Lexeme::Token(token) = lexeme else {
                continue;
            };
            if token.span().bytes() == b"propagate" {
                found = token.kind() == TokenKind::LowerWordForm
                    && candidate_fixed_terminal(token.span().bytes())
                        == Some(whitefoot::FixedTerminalV0_10::Try);
            }
        }
    }
    if !found {
        return Err(VerifyError::ParserProbe(
            "candidate fixed terminal did not follow the active lower-word lexer path".to_owned(),
        ));
    }
    Ok(())
}

fn run_parser_probe(source: &[u8]) -> Result<(), VerifyError> {
    let bundle = parser_probe_bundle(source)?;
    let lexed = match lex_v0_10(&bundle, parser_probe_lex_limits()) {
        LexOutcome::Complete(lexed) => lexed,
        outcome => return Err(VerifyError::ParserProbe(format!("lexing: {outcome:?}"))),
    };
    let classified = match classify_terminals_v0_10(
        &lexed,
        KERNEL_SPEC_V0_10_HASH,
        TerminalLimits { max_tokens: 256 },
    ) {
        TerminalOutcome::Complete(classified) => classified,
        outcome => {
            return Err(VerifyError::ParserProbe(format!(
                "terminal classification: {outcome:?}"
            )));
        }
    };
    match parse_v0_10(
        &classified,
        ParseLimits {
            max_work: 100_000,
            max_tasks: 4_096,
            max_frames: 512,
            max_elements: 4_096,
        },
    ) {
        ParseOutcome::Complete(_) => Ok(()),
        outcome => Err(VerifyError::ParserProbe(format!(
            "grammar derivation: {outcome:?}"
        ))),
    }
}

fn parser_probe_bundle(source: &[u8]) -> Result<SourceBundle, VerifyError> {
    let bundle = SourceBundle::with_limits(
        &[SourceInput::new("grammar-probe.wf", source)],
        SourceLimits {
            max_sources: 1,
            max_logical_path_bytes: 64,
            max_source_bytes: 4_096,
            max_total_source_bytes: 4_096,
            max_binding_bytes: 8_192,
        },
    )
    .map_err(|error| VerifyError::ParserProbe(format!("source bundle: {error}")))?;
    Ok(bundle)
}

const fn parser_probe_lex_limits() -> LexLimits {
    LexLimits {
        max_sources: 1,
        max_source_bytes: 4_096,
        max_total_source_bytes: 4_096,
        max_token_bytes: 256,
        max_tokens: 256,
        max_lexemes: 512,
    }
}

#[cfg(test)]
mod tests {
    use super::{ACTIVE_SPEC, ContractKind, VerifyError, verify_candidate};

    const PROPAGATE_CANDIDATE: &[u8] =
        include_bytes!("../../../governance/spec-evolution/kernel-spec-v0.11-candidate.md");

    #[test]
    fn exact_active_frontend_contract_verifies() {
        let report = verify_candidate(ACTIVE_SPEC).expect("active grammar must verify");
        assert_eq!(report.contract, ContractKind::Exact);
        assert_eq!(report.productions, 62);
        assert_eq!(report.decisions, 72);
        assert_eq!(report.terminals, 72);
    }

    #[test]
    fn exact_result_propagation_rename_verifies() {
        let report = verify_candidate(PROPAGATE_CANDIDATE)
            .expect("the one-for-one Result-propagation rename must verify");
        assert_eq!(report.contract, ContractKind::ResultPropagationRename);
        assert_eq!(report.productions, 62);
        assert_eq!(report.decisions, 72);
        assert_eq!(report.terminals, 72);
    }

    #[test]
    fn prose_outside_the_frontend_contract_may_change() {
        let mut proposal = ACTIVE_SPEC.to_vec();
        proposal.extend_from_slice(b"\nSemantic-only proposal text.\n");
        verify_candidate(&proposal).expect("semantic-only text must preserve the grammar");
    }

    #[test]
    fn changed_source_grammar_fails_closed() {
        let active = std::str::from_utf8(ACTIVE_SPEC).expect("active spec is UTF-8");
        let changed = active.replacen(
            "return_stmt := \"return\" expr \";\"",
            "return_stmt := \"return\" atom \";\"",
            1,
        );
        assert!(matches!(
            verify_candidate(changed.as_bytes()),
            Err(VerifyError::ChangedFrontendContract)
        ));
    }

    #[test]
    fn changed_comment_lexing_fails_closed() {
        let active = std::str::from_utf8(ACTIVE_SPEC).expect("active spec is UTF-8");
        let changed = active.replacen(
            "[FORM-4] There are no comments.",
            "[FORM-4] Line comments begin with two slash bytes.",
            1,
        );
        assert!(matches!(
            verify_candidate(changed.as_bytes()),
            Err(VerifyError::ChangedFrontendContract)
        ));
    }

    #[test]
    fn changed_unit_lexing_fails_closed() {
        let active = std::str::from_utf8(ACTIVE_SPEC).expect("active spec is UTF-8");
        let changed = active.replacen(
            "[FORM-6] The token `unit` names the unit type in type position and the unit value in expression position",
            "[FORM-6] The tokens `unit` and `void` name unit values in expression position",
            1,
        );
        assert!(matches!(
            verify_candidate(changed.as_bytes()),
            Err(VerifyError::ChangedFrontendContract)
        ));
    }

    #[test]
    fn partial_result_propagation_rename_fails_closed() {
        let candidate =
            std::str::from_utf8(PROPAGATE_CANDIDATE).expect("the candidate specification is UTF-8");
        let changed = candidate.replacen(
            "propagate_let_rhs := \"propagate\"",
            "try_let_rhs := \"propagate\"",
            1,
        );
        assert!(matches!(
            verify_candidate(changed.as_bytes()),
            Err(VerifyError::InvalidRename(_))
        ));
    }
}
