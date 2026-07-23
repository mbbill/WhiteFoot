use super::{compile, compile_and_run};

const GENERIC_INSTANCES: &[u8] = include_bytes!("../../../../tests/programs/generic_instances.wf");

#[test]
fn concrete_type_and_const_instances_have_distinct_symbols_and_execute() {
    let llvm = compile(GENERIC_INSTANCES);
    for name in ["maximum", "forward", "preserve"] {
        let symbol = format!("@wf_{name}$instance$");
        let definitions = llvm
            .lines()
            .filter(|line| line.starts_with("define internal") && line.contains(&symbol))
            .collect::<Vec<_>>();
        assert_eq!(definitions.len(), 2, "{name} definitions: {definitions:?}");
        assert_ne!(definitions[0], definitions[1]);
    }

    let output = compile_and_run(&llvm);
    assert!(output.status.success(), "{output:?}");
    assert!(output.stdout.is_empty());
    assert!(output.stderr.is_empty());
}

#[test]
fn concrete_generic_symbol_order_is_deterministic() {
    assert_eq!(compile(GENERIC_INSTANCES), compile(GENERIC_INSTANCES));
}
