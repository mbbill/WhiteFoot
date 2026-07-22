//! Conservative, pre-expansion Rust source miner used only to calibrate the
//! Leg-A reassociation proxy. It deliberately reports nearby unsupported
//! shapes instead of treating them as candidates.

use proc_macro2::{LineColumn, Span};
use quote::ToTokens;
use std::collections::{BTreeMap, BTreeSet, HashSet};
use syn::spanned::Spanned;
use syn::visit::{self, Visit};
use syn::{
    Block, Expr, ExprAssign, ExprClosure, ExprForLoop, ExprMethodCall, File, ImplItemFn, ItemFn,
    Lit, Local, Macro, Member, Pat, Stmt, TraitItemFn, Type,
};

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct Record {
    pub path: String,
    pub line: usize,
    pub column: usize,
    pub function: String,
    pub disposition: &'static str,
    pub class: String,
    pub law_requirement: &'static str,
    pub reason: String,
}

impl Record {
    pub fn to_json(&self) -> String {
        format!(
            "{{\"schema\":1,\"path\":\"{}\",\"line\":{},\"column\":{},\"function\":\"{}\",\"disposition\":\"{}\",\"class\":\"{}\",\"law_requirement\":\"{}\",\"reason\":\"{}\"}}",
            json_escape(&self.path),
            self.line,
            self.column,
            json_escape(&self.function),
            self.disposition,
            json_escape(&self.class),
            self.law_requirement,
            json_escape(&self.reason),
        )
    }
}

fn json_escape(value: &str) -> String {
    let mut out = String::new();
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if ch <= '\u{1f}' => out.push_str(&format!("\\u{:04x}", ch as u32)),
            ch => out.push(ch),
        }
    }
    out
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum NumericKind {
    Unsigned,
    Signed,
    Other,
    Unknown,
}

#[derive(Clone, Debug)]
struct LocalInfo {
    kind: NumericKind,
    zero: bool,
    mutable: bool,
    definition_clean: bool,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct PlaceKey {
    display: String,
    root: String,
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
struct SpanKey {
    start_line: usize,
    start_column: usize,
    end_line: usize,
    end_column: usize,
}

fn span_key(span: Span) -> SpanKey {
    let start = span.start();
    let end = span.end();
    SpanKey {
        start_line: start.line,
        start_column: start.column,
        end_line: end.line,
        end_column: end.column,
    }
}

fn record(
    path: &str,
    function: &str,
    span: Span,
    disposition: &'static str,
    class: &str,
    law_requirement: &'static str,
    reason: &str,
) -> Record {
    let LineColumn { line, column } = span.start();
    Record {
        path: path.to_owned(),
        line,
        column: column + 1,
        function: function.to_owned(),
        disposition,
        class: class.to_owned(),
        law_requirement,
        reason: reason.to_owned(),
    }
}

fn peel_expr(mut expr: &Expr) -> &Expr {
    loop {
        expr = match expr {
            Expr::Paren(node) => &node.expr,
            Expr::Group(node) => &node.expr,
            Expr::Reference(node) => &node.expr,
            _ => return expr,
        };
    }
}

fn simple_path(expr: &Expr) -> Option<String> {
    let Expr::Path(path) = peel_expr(expr) else {
        return None;
    };
    if path.qself.is_none() && path.path.segments.len() == 1 {
        Some(path.path.segments[0].ident.to_string())
    } else {
        None
    }
}

fn constant_index(expr: &Expr) -> Option<String> {
    let Expr::Lit(lit) = peel_expr(expr) else {
        return None;
    };
    let Lit::Int(value) = &lit.lit else {
        return None;
    };
    value.base10_parse::<usize>().ok().map(|v| v.to_string())
}

fn place_key(expr: &Expr) -> Option<PlaceKey> {
    match peel_expr(expr) {
        Expr::Path(_) => simple_path(expr).map(|name| PlaceKey {
            display: name.clone(),
            root: name,
        }),
        Expr::Index(node) => {
            let base = place_key(&node.expr)?;
            if base.display != base.root {
                return None;
            }
            let index = constant_index(&node.index)?;
            Some(PlaceKey {
                display: format!("{}[{index}]", base.root),
                root: base.root,
            })
        }
        Expr::Field(node) => {
            let base = place_key(&node.base)?;
            if base.display != base.root {
                return None;
            }
            let field = match &node.member {
                Member::Named(name) => name.to_string(),
                Member::Unnamed(index) => index.index.to_string(),
            };
            Some(PlaceKey {
                display: format!("{}.{field}", base.root),
                root: base.root,
            })
        }
        _ => None,
    }
}

fn kind_from_ident(name: &str) -> NumericKind {
    match name {
        "u8" | "u16" | "u32" | "u64" | "u128" | "usize" => NumericKind::Unsigned,
        "i8" | "i16" | "i32" | "i64" | "i128" | "isize" => NumericKind::Signed,
        _ => NumericKind::Other,
    }
}

fn kind_from_type(ty: &Type) -> NumericKind {
    match ty {
        Type::Path(path) if path.qself.is_none() && path.path.segments.len() == 1 => {
            kind_from_ident(&path.path.segments[0].ident.to_string())
        }
        Type::Paren(paren) => kind_from_type(&paren.elem),
        Type::Group(group) => kind_from_type(&group.elem),
        _ => NumericKind::Unknown,
    }
}

fn kind_from_expr(expr: &Expr) -> NumericKind {
    match peel_expr(expr) {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Int(value) if !value.suffix().is_empty() => kind_from_ident(value.suffix()),
            _ => NumericKind::Unknown,
        },
        Expr::Cast(cast) => kind_from_type(&cast.ty),
        _ => NumericKind::Unknown,
    }
}

fn expr_is_zero(expr: &Expr) -> bool {
    match peel_expr(expr) {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Int(value) => value.base10_parse::<u128>().is_ok_and(|value| value == 0),
            _ => false,
        },
        Expr::Repeat(repeat) => expr_is_zero(&repeat.expr),
        Expr::Array(array) => !array.elems.is_empty() && array.elems.iter().all(expr_is_zero),
        Expr::Cast(cast) => expr_is_zero(&cast.expr),
        _ => false,
    }
}

fn local_binding(local: &Local) -> Option<(String, bool, Option<&Type>)> {
    match &local.pat {
        Pat::Ident(binding) => Some((
            binding.ident.to_string(),
            binding.mutability.is_some(),
            None,
        )),
        Pat::Type(typed) => {
            let Pat::Ident(binding) = typed.pat.as_ref() else {
                return None;
            };
            Some((
                binding.ident.to_string(),
                binding.mutability.is_some(),
                Some(typed.ty.as_ref()),
            ))
        }
        _ => None,
    }
}

fn add_local(env: &mut BTreeMap<String, LocalInfo>, local: &Local) {
    let Some((name, mutable, explicit_ty)) = local_binding(local) else {
        return;
    };
    let init = local.init.as_ref().map(|init| init.expr.as_ref());
    let explicit = explicit_ty
        .map(kind_from_type)
        .unwrap_or(NumericKind::Unknown);
    let inferred = init.map(kind_from_expr).unwrap_or(NumericKind::Unknown);
    let kind = if explicit != NumericKind::Unknown {
        explicit
    } else {
        inferred
    };
    let zero = init.is_some_and(expr_is_zero);
    let info = LocalInfo {
        kind,
        zero,
        mutable,
        definition_clean: true,
    };
    if env.insert(name.clone(), info).is_some() {
        env.insert(
            name,
            LocalInfo {
                kind: NumericKind::Unknown,
                zero: false,
                mutable: false,
                definition_clean: false,
            },
        );
    }
}

struct BindingCollector {
    names: BTreeSet<String>,
}

impl<'ast> Visit<'ast> for BindingCollector {
    fn visit_local(&mut self, node: &'ast Local) {
        self.names.extend(pat_idents(&node.pat));
        if let Some(init) = &node.init {
            self.visit_expr(&init.expr);
        }
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}
}

struct MacroTokenCollector {
    tokens: Vec<String>,
}

impl<'ast> Visit<'ast> for MacroTokenCollector {
    fn visit_macro(&mut self, node: &'ast Macro) {
        self.tokens.push(node.tokens.to_token_stream().to_string());
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}
}

fn token_mentions(tokens: &str, name: &str) -> bool {
    tokens.split_whitespace().any(|token| token == name)
}

fn taint_env_from_stmt(env: &mut BTreeMap<String, LocalInfo>, stmt: &Stmt) {
    let used_roots: BTreeSet<_> = stmt_places(stmt)
        .keys()
        .map(|place| place.root.clone())
        .collect();
    let mut bindings = BindingCollector {
        names: BTreeSet::new(),
    };
    bindings.visit_stmt(stmt);
    let mut macros = MacroTokenCollector { tokens: Vec::new() };
    macros.visit_stmt(stmt);
    for (name, info) in env {
        if used_roots.contains(name)
            || bindings.names.contains(name)
            || macros
                .tokens
                .iter()
                .any(|tokens| token_mentions(tokens, name))
        {
            info.definition_clean = false;
        }
    }
}

fn taint_env_from_expr(env: &mut BTreeMap<String, LocalInfo>, expr: &Expr) {
    let used_roots: BTreeSet<_> = expr_places(expr)
        .keys()
        .map(|place| place.root.clone())
        .collect();
    let mut bindings = BindingCollector {
        names: BTreeSet::new(),
    };
    bindings.visit_expr(expr);
    let mut macros = MacroTokenCollector { tokens: Vec::new() };
    macros.visit_expr(expr);
    for (name, info) in env {
        if used_roots.contains(name)
            || bindings.names.contains(name)
            || macros
                .tokens
                .iter()
                .any(|tokens| token_mentions(tokens, name))
        {
            info.definition_clean = false;
        }
    }
}

fn pat_idents(pat: &Pat) -> BTreeSet<String> {
    struct Collector {
        names: BTreeSet<String>,
    }
    impl<'ast> Visit<'ast> for Collector {
        fn visit_pat_ident(&mut self, node: &'ast syn::PatIdent) {
            self.names.insert(node.ident.to_string());
            visit::visit_pat_ident(self, node);
        }
    }
    let mut collector = Collector {
        names: BTreeSet::new(),
    };
    collector.visit_pat(pat);
    collector.names
}

struct PlaceUseCollector {
    places: BTreeMap<PlaceKey, usize>,
}

impl<'ast> Visit<'ast> for PlaceUseCollector {
    fn visit_expr(&mut self, node: &'ast Expr) {
        if let Some(place) = place_key(node) {
            *self.places.entry(place).or_default() += 1;
            return;
        }
        visit::visit_expr(self, node);
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}

    fn visit_impl_item_fn(&mut self, _node: &'ast ImplItemFn) {}

    fn visit_trait_item_fn(&mut self, _node: &'ast TraitItemFn) {}
}

fn expr_places(expr: &Expr) -> BTreeMap<PlaceKey, usize> {
    let mut collector = PlaceUseCollector {
        places: BTreeMap::new(),
    };
    collector.visit_expr(expr);
    collector.places
}

fn stmt_places(stmt: &Stmt) -> BTreeMap<PlaceKey, usize> {
    let mut collector = PlaceUseCollector {
        places: BTreeMap::new(),
    };
    collector.visit_stmt(stmt);
    collector.places
}

#[derive(Clone)]
struct Recurrence<'ast> {
    place: PlaceKey,
    call: &'ast ExprMethodCall,
    operand: &'ast Expr,
    assign_span: Span,
}

fn as_saturating_recurrence(assign: &ExprAssign) -> Option<Recurrence<'_>> {
    let place = place_key(&assign.left)?;
    let Expr::MethodCall(call) = peel_expr(&assign.right) else {
        return None;
    };
    if call.method != "saturating_add" || call.args.len() != 1 {
        return None;
    }
    if place_key(&call.receiver).as_ref() != Some(&place) {
        return None;
    }
    Some(Recurrence {
        place,
        call,
        operand: &call.args[0],
        assign_span: assign.span(),
    })
}

struct RecurrenceCollector<'ast> {
    recurrences: Vec<Recurrence<'ast>>,
}

impl<'ast> Visit<'ast> for RecurrenceCollector<'ast> {
    fn visit_expr_assign(&mut self, node: &'ast ExprAssign) {
        if let Some(recurrence) = as_saturating_recurrence(node) {
            self.recurrences.push(recurrence);
        }
        visit::visit_expr_assign(self, node);
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}

    fn visit_impl_item_fn(&mut self, _node: &'ast ImplItemFn) {}

    fn visit_trait_item_fn(&mut self, _node: &'ast TraitItemFn) {}
}

fn loop_recurrences(loop_expr: &ExprForLoop) -> Vec<Recurrence<'_>> {
    loop_expr
        .body
        .stmts
        .iter()
        .filter_map(|stmt| {
            let Stmt::Expr(Expr::Assign(assign), _) = stmt else {
                return None;
            };
            as_saturating_recurrence(assign)
        })
        .collect()
}

struct MethodCollector<'ast> {
    saturating_adds: Vec<&'ast ExprMethodCall>,
    folds: Vec<&'ast ExprMethodCall>,
    opaque_closures: Vec<&'ast ExprClosure>,
}

impl<'ast> Visit<'ast> for MethodCollector<'ast> {
    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        let is_fold = matches!(
            node.method.to_string().as_str(),
            "fold" | "try_fold" | "reduce" | "try_reduce"
        );
        if is_fold {
            self.folds.push(node);
            self.visit_expr(&node.receiver);
            for argument in &node.args {
                if !matches!(argument, Expr::Closure(_)) {
                    self.visit_expr(argument);
                }
            }
            return;
        }
        if node.method == "saturating_add" {
            self.saturating_adds.push(node);
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_closure(&mut self, node: &'ast ExprClosure) {
        let tokens = node.body.to_token_stream().to_string();
        if tokens.contains("saturating_add")
            || tokens.contains(". fold")
            || tokens.contains(". reduce")
        {
            self.opaque_closures.push(node);
        }
    }

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}

    fn visit_impl_item_fn(&mut self, _node: &'ast ImplItemFn) {}

    fn visit_trait_item_fn(&mut self, _node: &'ast TraitItemFn) {}
}

fn collect_method_calls(block: &Block) -> MethodCollector<'_> {
    let mut collector = MethodCollector {
        saturating_adds: Vec::new(),
        folds: Vec::new(),
        opaque_closures: Vec::new(),
    };
    collector.visit_block(block);
    collector
}

fn saturating_calls_in_method(call: &ExprMethodCall) -> Vec<SpanKey> {
    let mut collector = MethodCollector {
        saturating_adds: Vec::new(),
        folds: Vec::new(),
        opaque_closures: Vec::new(),
    };
    collector.visit_expr_method_call(call);
    collector
        .saturating_adds
        .into_iter()
        .map(|node| span_key(node.span()))
        .collect()
}

fn merge_leaves(expr: &Expr) -> Option<BTreeMap<PlaceKey, usize>> {
    let expr = peel_expr(expr);
    if let Some(place) = place_key(expr) {
        return Some(BTreeMap::from([(place, 1)]));
    }
    let Expr::MethodCall(call) = expr else {
        return None;
    };
    if call.method != "saturating_add" || call.args.len() != 1 {
        return None;
    }
    let mut leaves = merge_leaves(&call.receiver)?;
    for (place, count) in merge_leaves(&call.args[0])? {
        *leaves.entry(place).or_default() += count;
    }
    Some(leaves)
}

struct MergeFinder<'a> {
    required: &'a BTreeMap<PlaceKey, usize>,
    spans: Option<Vec<SpanKey>>,
}

impl<'ast> Visit<'ast> for MergeFinder<'_> {
    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if self.spans.is_none() && node.method == "saturating_add" {
            let expr = Expr::MethodCall(node.clone());
            if merge_leaves(&expr).as_ref() == Some(self.required) {
                self.spans = Some(saturating_calls_in_method(node));
                return;
            }
        }
        visit::visit_expr_method_call(self, node);
    }
}

fn merge_in_stmt(stmt: &Stmt, required: &BTreeMap<PlaceKey, usize>) -> Option<Vec<SpanKey>> {
    let mut finder = MergeFinder {
        required,
        spans: None,
    };
    finder.visit_stmt(stmt);
    finder.spans
}

fn binding_names(stmt: &Stmt) -> BTreeSet<String> {
    let Stmt::Local(local) = stmt else {
        return BTreeSet::new();
    };
    pat_idents(&local.pat)
}

fn first_use_merge(
    following: &[Stmt],
    required: &BTreeMap<PlaceKey, usize>,
) -> Option<Vec<SpanKey>> {
    let roots: BTreeSet<_> = required.keys().map(|place| place.root.clone()).collect();
    for stmt in following {
        if !binding_names(stmt).is_disjoint(&roots) {
            return None;
        }
        let mut macros = MacroTokenCollector { tokens: Vec::new() };
        macros.visit_stmt(stmt);
        if macros
            .tokens
            .iter()
            .any(|tokens| roots.iter().any(|root| token_mentions(tokens, root)))
        {
            return None;
        }
        let uses: BTreeMap<_, _> = stmt_places(stmt)
            .into_iter()
            .filter(|(place, _)| roots.contains(&place.root))
            .collect();
        if !uses.is_empty() {
            if &uses != required {
                return None;
            }
            return merge_in_stmt(stmt, required);
        }
    }
    None
}

fn is_assign_binop(op: &syn::BinOp) -> bool {
    matches!(
        op,
        syn::BinOp::AddAssign(_)
            | syn::BinOp::SubAssign(_)
            | syn::BinOp::MulAssign(_)
            | syn::BinOp::DivAssign(_)
            | syn::BinOp::RemAssign(_)
            | syn::BinOp::BitXorAssign(_)
            | syn::BinOp::BitAndAssign(_)
            | syn::BinOp::BitOrAssign(_)
            | syn::BinOp::ShlAssign(_)
            | syn::BinOp::ShrAssign(_)
    )
}

fn conflicts(place: &PlaceKey, targets: &BTreeSet<PlaceKey>) -> bool {
    targets.iter().any(|target| target.root == place.root)
}

fn assigned_places(expr: &Expr) -> BTreeSet<PlaceKey> {
    let expr = peel_expr(expr);
    if let Some(place) = place_key(expr) {
        return BTreeSet::from([place]);
    }
    match expr {
        Expr::Tuple(tuple) => tuple.elems.iter().flat_map(assigned_places).collect(),
        Expr::Array(array) => array.elems.iter().flat_map(assigned_places).collect(),
        _ => BTreeSet::new(),
    }
}

fn expr_uses_targets(expr: &Expr, targets: &BTreeSet<PlaceKey>) -> bool {
    expr_places(expr)
        .keys()
        .any(|place| conflicts(place, targets))
}

struct AccessCollector<'a> {
    targets: &'a BTreeSet<PlaceKey>,
    read: bool,
    write: bool,
}

impl<'ast> Visit<'ast> for AccessCollector<'_> {
    fn visit_expr(&mut self, node: &'ast Expr) {
        if let Some(place) = place_key(node) {
            if conflicts(&place, self.targets) {
                self.read = true;
            }
            return;
        }
        visit::visit_expr(self, node);
    }

    fn visit_expr_assign(&mut self, node: &'ast ExprAssign) {
        if assigned_places(&node.left)
            .iter()
            .any(|place| conflicts(place, self.targets))
        {
            self.write = true;
        } else {
            self.visit_expr(&node.left);
        }
        self.visit_expr(&node.right);
    }

    fn visit_expr_binary(&mut self, node: &'ast syn::ExprBinary) {
        if is_assign_binop(&node.op) {
            if place_key(&node.left).is_some_and(|place| conflicts(&place, self.targets)) {
                self.write = true;
            } else {
                self.visit_expr(&node.left);
            }
            self.visit_expr(&node.right);
            return;
        }
        visit::visit_expr_binary(self, node);
    }

    fn visit_local(&mut self, node: &'ast Local) {
        let names = pat_idents(&node.pat);
        if self
            .targets
            .iter()
            .any(|target| names.contains(&target.root))
        {
            self.write = true;
        }
        if let Some(init) = &node.init {
            self.visit_expr(&init.expr);
        }
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        if expr_uses_targets(&node.receiver, self.targets)
            || node
                .args
                .iter()
                .any(|argument| expr_uses_targets(argument, self.targets))
        {
            self.write = true;
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if node
            .args
            .iter()
            .any(|argument| expr_uses_targets(argument, self.targets))
        {
            self.write = true;
        }
        visit::visit_expr_call(self, node);
    }

    fn visit_expr_reference(&mut self, node: &'ast syn::ExprReference) {
        if node.mutability.is_some() && expr_uses_targets(&node.expr, self.targets) {
            self.write = true;
        }
        visit::visit_expr_reference(self, node);
    }

    fn visit_expr_macro(&mut self, node: &'ast syn::ExprMacro) {
        let tokens = node.mac.tokens.to_token_stream().to_string();
        if self
            .targets
            .iter()
            .any(|target| tokens.split_whitespace().any(|token| token == target.root))
        {
            self.write = true;
        }
    }

    fn visit_stmt_macro(&mut self, node: &'ast syn::StmtMacro) {
        let tokens = node.mac.tokens.to_token_stream().to_string();
        if self
            .targets
            .iter()
            .any(|target| tokens.split_whitespace().any(|token| token == target.root))
        {
            self.write = true;
        }
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {}

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {}
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum PostLoopAccess {
    Read,
    Overwrite,
    None,
}

fn first_post_loop_access(following: &[Stmt], place: &PlaceKey) -> PostLoopAccess {
    let targets = BTreeSet::from([place.clone()]);
    for stmt in following {
        let mut access = AccessCollector {
            targets: &targets,
            read: false,
            write: false,
        };
        access.visit_stmt(stmt);
        if access.write {
            return PostLoopAccess::Overwrite;
        }
        if access.read {
            return PostLoopAccess::Read;
        }
    }
    PostLoopAccess::None
}

fn info_for_place<'a>(
    env: &'a BTreeMap<String, LocalInfo>,
    place: &PlaceKey,
) -> Option<&'a LocalInfo> {
    env.get(&place.root)
}

fn update_mentions_lane(update: &Recurrence<'_>, lanes: &BTreeSet<PlaceKey>) -> bool {
    expr_places(update.operand)
        .keys()
        .any(|place| conflicts(place, lanes))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ItemSelector {
    Direct,
}

fn selector_expr(mut expr: &Expr) -> &Expr {
    loop {
        expr = match expr {
            Expr::Paren(node) => &node.expr,
            Expr::Group(node) => &node.expr,
            Expr::Cast(node) => &node.expr,
            _ => return expr,
        };
    }
}

fn item_selector(expr: &Expr, item: &str) -> Option<ItemSelector> {
    let expr = selector_expr(expr);
    if simple_path(expr).as_deref() == Some(item) {
        return Some(ItemSelector::Direct);
    }
    None
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum LoopBodyIssue {
    BindingShadow,
    Escape,
    OpaqueMacro,
    OpaqueCall,
    OtherWrite,
    OtherStatement,
}

impl LoopBodyIssue {
    fn class(self) -> &'static str {
        match self {
            Self::BindingShadow => "loop_body_binding_shadow",
            Self::Escape => "loop_body_accumulator_escape",
            Self::OpaqueMacro => "loop_body_opaque_macro",
            Self::OpaqueCall => "loop_body_opaque_call",
            Self::OtherWrite => "loop_body_other_write",
            Self::OtherStatement => "loop_body_other_statement",
        }
    }

    fn reason(self) -> &'static str {
        match self {
            Self::BindingShadow => "a loop-body binding shadows an accumulator root",
            Self::Escape => "the loop body borrows or otherwise exposes accumulator storage",
            Self::OpaqueMacro => "a macro in the loop body is opaque before expansion",
            Self::OpaqueCall => "a call in the loop body has unresolved effects or ordering",
            Self::OtherWrite => "the loop body contains a reset or another write",
            Self::OtherStatement => {
                "the loop body is not exactly the recognized recurrence statements"
            }
        }
    }
}

struct HazardCollector<'a> {
    roots: &'a BTreeSet<String>,
    binding_shadow: bool,
    escape: bool,
    opaque_macro: bool,
    opaque_call: bool,
    other_write: bool,
}

impl HazardCollector<'_> {
    fn issue(&self) -> Option<LoopBodyIssue> {
        if self.binding_shadow {
            Some(LoopBodyIssue::BindingShadow)
        } else if self.escape {
            Some(LoopBodyIssue::Escape)
        } else if self.opaque_macro {
            Some(LoopBodyIssue::OpaqueMacro)
        } else if self.other_write {
            Some(LoopBodyIssue::OtherWrite)
        } else if self.opaque_call {
            Some(LoopBodyIssue::OpaqueCall)
        } else {
            None
        }
    }

    fn expression_uses_root(&self, expr: &Expr) -> bool {
        expr_places(expr)
            .keys()
            .any(|place| self.roots.contains(&place.root))
    }
}

impl<'ast> Visit<'ast> for HazardCollector<'_> {
    fn visit_local(&mut self, node: &'ast Local) {
        if local_binding(node).is_some_and(|(name, _, _)| self.roots.contains(&name)) {
            self.binding_shadow = true;
        }
        visit::visit_local(self, node);
    }

    fn visit_expr_reference(&mut self, node: &'ast syn::ExprReference) {
        if self.expression_uses_root(&node.expr) {
            self.escape = true;
        }
        visit::visit_expr_reference(self, node);
    }

    fn visit_expr_macro(&mut self, _node: &'ast syn::ExprMacro) {
        self.opaque_macro = true;
    }

    fn visit_stmt_macro(&mut self, _node: &'ast syn::StmtMacro) {
        self.opaque_macro = true;
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        self.opaque_call = true;
        visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        self.opaque_call = true;
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_assign(&mut self, node: &'ast ExprAssign) {
        self.other_write = true;
        visit::visit_expr_assign(self, node);
    }

    fn visit_expr_binary(&mut self, node: &'ast syn::ExprBinary) {
        if is_assign_binop(&node.op) {
            self.other_write = true;
        }
        visit::visit_expr_binary(self, node);
    }

    fn visit_expr_closure(&mut self, _node: &'ast ExprClosure) {
        self.opaque_call = true;
    }

    fn visit_item_fn(&mut self, _node: &'ast ItemFn) {
        self.opaque_call = true;
    }
}

fn hazards_in_expr(expr: &Expr, roots: &BTreeSet<String>) -> Option<LoopBodyIssue> {
    let mut hazards = HazardCollector {
        roots,
        binding_shadow: false,
        escape: false,
        opaque_macro: false,
        opaque_call: false,
        other_write: false,
    };
    hazards.visit_expr(expr);
    hazards.issue()
}

fn hazards_in_stmt(stmt: &Stmt, roots: &BTreeSet<String>) -> LoopBodyIssue {
    let mut hazards = HazardCollector {
        roots,
        binding_shadow: false,
        escape: false,
        opaque_macro: false,
        opaque_call: false,
        other_write: false,
    };
    hazards.visit_stmt(stmt);
    hazards.issue().unwrap_or(LoopBodyIssue::OtherStatement)
}

fn loop_body_issue(loop_expr: &ExprForLoop, updates: &[Recurrence<'_>]) -> Option<LoopBodyIssue> {
    let roots: BTreeSet<_> = updates
        .iter()
        .map(|update| update.place.root.clone())
        .collect();
    for stmt in &loop_expr.body.stmts {
        let direct = match stmt {
            Stmt::Expr(Expr::Assign(assign), _) => as_saturating_recurrence(assign),
            _ => None,
        };
        if let Some(recurrence) = direct {
            if let Some(issue) = hazards_in_expr(recurrence.operand, &roots) {
                return Some(issue);
            }
        } else {
            return Some(hazards_in_stmt(stmt, &roots));
        }
    }
    None
}

fn manual_index_topology(updates: &[Recurrence<'_>], item_names: &BTreeSet<String>) -> bool {
    let _ = (updates, item_names);
    false
}

fn analyze_loop(
    path: &str,
    function: &str,
    loop_expr: &ExprForLoop,
    following: &[Stmt],
    env: &BTreeMap<String, LocalInfo>,
    consumed: &mut HashSet<SpanKey>,
    records: &mut Vec<Record>,
) {
    let mut reaching_env = env.clone();
    taint_env_from_expr(&mut reaching_env, &loop_expr.expr);
    let updates = loop_recurrences(loop_expr);
    if updates.is_empty() {
        return;
    }
    let loop_methods = collect_method_calls(&loop_expr.body);
    consumed.extend(
        loop_methods
            .saturating_adds
            .into_iter()
            .map(|call| span_key(call.span())),
    );
    let item_names = pat_idents(&loop_expr.pat);
    let lanes: BTreeSet<_> = updates.iter().map(|update| update.place.clone()).collect();
    for update in &updates {
        consumed.insert(span_key(update.call.span()));
    }
    let body_issue = loop_body_issue(loop_expr, &updates);

    if lanes.len() >= 2 {
        let lane_roots: BTreeSet<_> = updates
            .iter()
            .map(|update| update.place.root.clone())
            .collect();
        let binding_shadowed = !item_names.is_disjoint(&lane_roots);
        let distinct_once = lanes.len() == updates.len();
        let infos: Vec<_> = updates
            .iter()
            .map(|update| info_for_place(&reaching_env, &update.place))
            .collect();
        let all_mutable = infos
            .iter()
            .all(|info| info.is_some_and(|info| info.mutable));
        let all_zero = infos.iter().all(|info| info.is_some_and(|info| info.zero));
        let all_clean = infos
            .iter()
            .all(|info| info.is_some_and(|info| info.definition_clean));
        let independent = updates
            .iter()
            .all(|update| !update_mentions_lane(update, &lanes));
        let topology = manual_index_topology(&updates, &item_names);
        let required: BTreeMap<_, _> = lanes.iter().cloned().map(|lane| (lane, 1)).collect();
        let merge = first_use_merge(following, &required);

        let (disposition, class, reason) = if binding_shadowed {
            (
                "unresolved",
                "manual_multilane_binding_shadowed",
                "a loop-pattern binding shadows a lane root",
            )
        } else if let Some(issue) = body_issue {
            ("unresolved", issue.class(), issue.reason())
        } else if !distinct_once || !independent {
            (
                "unresolved",
                "manual_multilane_dependency_unresolved",
                "lanes are updated more than once or an update reads another lane",
            )
        } else if !all_mutable {
            (
                "unresolved",
                "manual_multilane_binding_unresolved",
                "lane roots are not uniquely mutable source bindings",
            )
        } else if !all_zero {
            (
                "unresolved",
                "manual_multilane_identity_unresolved",
                "source syntax does not establish zero initialization for every lane",
            )
        } else if !all_clean {
            (
                "unresolved",
                "manual_multilane_reaching_definition_unresolved",
                "a pre-loop use, write, recurrence, or shadow may replace a lane initializer",
            )
        } else if merge.is_none() {
            (
                "unresolved",
                "manual_multilane_merge_unresolved",
                "the first post-loop lane use is not an exact same-operation merge tree",
            )
        } else if !topology {
            (
                "unresolved",
                "manual_multilane_role_unresolved",
                "stage-1 syntax cannot distinguish separate statistics from reassociation lanes",
            )
        } else {
            (
                "unresolved",
                "manual_multilane_semantics_unresolved",
                "the source has an exact lane-and-merge shape, but stage 1 cannot prove primitive method identity or one logical reduction",
            )
        };
        if let Some(spans) = merge {
            consumed.extend(spans);
        }
        records.push(record(
            path,
            function,
            loop_expr.span(),
            disposition,
            class,
            "unknown",
            reason,
        ));
        return;
    }

    let update = &updates[0];
    let info = info_for_place(&reaching_env, &update.place);
    let binding_shadowed = item_names.contains(&update.place.root);
    let item_derived = item_names.len() == 1
        && item_selector(
            update.operand,
            item_names.first().expect("one item binding"),
        )
        .is_some();
    let operand_mentions_item = item_names.len() == 1
        && expr_places(update.operand)
            .keys()
            .any(|place| place.root == *item_names.first().expect("one item binding"));
    let post_access = first_post_loop_access(following, &update.place);
    let (disposition, class, law, reason) = if binding_shadowed {
        (
            "unresolved",
            "sequential_binding_shadowed",
            "unknown",
            "the for-loop pattern shadows the accumulator root",
        )
    } else if let Some(issue) = body_issue {
        ("unresolved", issue.class(), "unknown", issue.reason())
    } else if updates.len() != 1 {
        (
            "unresolved",
            "sequential_recurrence_multiple_updates",
            "unknown",
            "the accumulator is updated more than once in the loop body",
        )
    } else if info.is_none_or(|info| !info.mutable) {
        (
            "unresolved",
            "sequential_binding_unresolved",
            "unknown",
            "the accumulator is not a uniquely mutable source binding",
        )
    } else if update.place.display != update.place.root {
        (
            "unresolved",
            "sequential_non_scalar_accumulator_unresolved",
            "unknown",
            "stage-1 candidates require a primitive scalar binding, not an indexed or field place",
        )
    } else if info.is_some_and(|info| info.kind == NumericKind::Signed) {
        (
            "excluded",
            "known_nonassociative_signed_saturating_add",
            "none",
            "signed saturating addition is not associative",
        )
    } else if info.is_none_or(|info| info.kind != NumericKind::Unsigned) {
        (
            "unresolved",
            "sequential_accumulator_type_unresolved",
            "unknown",
            "source syntax does not establish an unsigned primitive accumulator type",
        )
    } else if info.is_none_or(|info| !info.zero) {
        (
            "unresolved",
            "sequential_identity_unresolved",
            "unknown",
            "source syntax does not establish the zero identity initializer",
        )
    } else if info.is_none_or(|info| !info.definition_clean) {
        (
            "unresolved",
            "sequential_reaching_definition_unresolved",
            "unknown",
            "a pre-loop use, write, recurrence, or shadow may replace the zero initializer",
        )
    } else if operand_mentions_item && !item_derived {
        (
            "unresolved",
            "sequential_item_projection_unresolved",
            "unknown",
            "the operand mentions the loop item through dereference, indexing, or another source-only-unresolved projection",
        )
    } else if !item_derived {
        (
            "excluded",
            "constant_or_induction_saturating_accumulation",
            "none",
            "the update is not data-dependent on the for-loop item",
        )
    } else if post_access == PostLoopAccess::Overwrite {
        (
            "excluded",
            "post_loop_accumulator_overwritten",
            "none",
            "the first post-loop accumulator access overwrites it",
        )
    } else if post_access == PostLoopAccess::None {
        (
            "excluded",
            "unobserved_saturating_recurrence",
            "none",
            "the accumulator is not observed after the loop",
        )
    } else {
        (
            "candidate",
            "sequential_unsigned_saturating_add",
            "associative+commutative+identity",
            "zero-initialized unsigned recurrence consumes loop-item-derived data",
        )
    };
    records.push(record(
        path,
        function,
        update.assign_span,
        disposition,
        class,
        law,
        reason,
    ));
}

fn closure_exact_saturating_fold(call: &ExprMethodCall) -> bool {
    if call.method != "fold" || call.args.len() != 2 {
        return false;
    }
    let init = &call.args[0];
    if kind_from_expr(init) != NumericKind::Unsigned || !expr_is_zero(init) {
        return false;
    }
    let Expr::Closure(ExprClosure { inputs, body, .. }) = &call.args[1] else {
        return false;
    };
    if inputs.len() != 2 {
        return false;
    }
    let acc_names = pat_idents(&inputs[0]);
    let item_names = pat_idents(&inputs[1]);
    if acc_names.len() != 1 || item_names.len() != 1 {
        return false;
    }
    let body = match peel_expr(body) {
        Expr::Block(block) => block.block.stmts.last().and_then(|stmt| match stmt {
            Stmt::Expr(expr, None) => Some(expr),
            _ => None,
        }),
        expr => Some(expr),
    };
    let Some(Expr::MethodCall(reducer)) = body.map(peel_expr) else {
        return false;
    };
    reducer.method == "saturating_add"
        && reducer.args.len() == 1
        && simple_path(&reducer.receiver).is_some_and(|name| acc_names.contains(&name))
        && item_selector(
            &reducer.args[0],
            item_names.first().expect("one item binding"),
        )
        .is_some()
}

fn analyze_function(path: &str, function: &str, block: &Block) -> Vec<Record> {
    let methods = collect_method_calls(block);
    let mut records = Vec::new();
    let mut consumed = HashSet::new();

    for fold in methods.folds.iter().copied() {
        consumed.extend(saturating_calls_in_method(fold));
        let exact = closure_exact_saturating_fold(fold);
        records.push(record(
            path,
            function,
            fold.span(),
            "unresolved",
            if exact {
                "fold_method_semantics_unresolved"
            } else {
                "fold_shape_unresolved"
            },
            "unknown",
            if exact {
                "the reducer is syntactically unsigned saturating-add, but source parsing cannot distinguish core Iterator::fold from Rayon or a custom method"
            } else {
                "fold/reduce is outside the calibration recognizer or requires semantic/dataflow resolution"
            },
        ));
    }
    for closure in &methods.opaque_closures {
        records.push(record(
            path,
            &format!("{function}::<closure>"),
            closure.span(),
            "unresolved",
            "closure_body_unresolved",
            "unknown",
            "stage-1 does not attribute recurrence or fold sites through closure boundaries",
        ));
    }

    let mut env = BTreeMap::new();
    for (index, stmt) in block.stmts.iter().enumerate() {
        if let Stmt::Local(local) = stmt {
            taint_env_from_stmt(&mut env, stmt);
            add_local(&mut env, local);
            continue;
        }
        if let Stmt::Expr(Expr::ForLoop(loop_expr), _) = stmt {
            analyze_loop(
                path,
                function,
                loop_expr,
                &block.stmts[index + 1..],
                &env,
                &mut consumed,
                &mut records,
            );
        }
        taint_env_from_stmt(&mut env, stmt);
    }

    let mut all_recurrences = RecurrenceCollector {
        recurrences: Vec::new(),
    };
    all_recurrences.visit_block(block);
    for recurrence in all_recurrences.recurrences {
        let key = span_key(recurrence.call.span());
        if consumed.insert(key) {
            records.push(record(
                path,
                function,
                recurrence.assign_span,
                "unresolved",
                "recurrence_context_unresolved",
                "unknown",
                "self recurrence occurs outside a directly sequenced top-level for-loop",
            ));
        }
    }

    for call in methods.saturating_adds {
        if consumed.insert(span_key(call.span())) {
            records.push(record(
                path,
                function,
                call.span(),
                "excluded",
                "non_recurrence_saturating_add",
                "none",
                "saturating_add is not the recognized self-recurrence assignment shape",
            ));
        }
    }
    records
}

struct FunctionAnalyzer<'a> {
    path: &'a str,
    records: Vec<Record>,
    stack: Vec<String>,
}

impl FunctionAnalyzer<'_> {
    fn analyze_named(&mut self, name: String, block: &Block) {
        let function = if self.stack.is_empty() {
            name.clone()
        } else {
            format!("{}::{name}", self.stack.join("::"))
        };
        self.records
            .extend(analyze_function(self.path, &function, block));
        self.stack.push(name);
        self.visit_block(block);
        self.stack.pop();
    }
}

impl<'ast> Visit<'ast> for FunctionAnalyzer<'_> {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        self.analyze_named(node.sig.ident.to_string(), &node.block);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast ImplItemFn) {
        self.analyze_named(node.sig.ident.to_string(), &node.block);
    }

    fn visit_trait_item_fn(&mut self, node: &'ast TraitItemFn) {
        if let Some(default) = &node.default {
            self.analyze_named(node.sig.ident.to_string(), default);
        }
    }
}

struct MacroCollector<'a> {
    path: &'a str,
    records: Vec<Record>,
}

impl MacroCollector<'_> {
    fn inspect(&mut self, node: &Macro) {
        let tokens = node.tokens.to_token_stream().to_string();
        if tokens.contains("saturating_add")
            || tokens.contains(". fold")
            || tokens.contains(". reduce")
        {
            self.records.push(record(
                self.path,
                "<macro>",
                node.span(),
                "unresolved",
                "macro_tokens_unresolved",
                "unknown",
                "the source miner does not parse or expand Rust code inside macro tokens",
            ));
        }
    }
}

impl<'ast> Visit<'ast> for MacroCollector<'_> {
    fn visit_macro(&mut self, node: &'ast Macro) {
        self.inspect(node);
    }
}

pub fn analyze_source(path: &str, source: &str) -> Result<Vec<Record>, String> {
    let file: File = syn::parse_file(source).map_err(|error| error.to_string())?;
    let mut functions = FunctionAnalyzer {
        path,
        records: Vec::new(),
        stack: Vec::new(),
    };
    functions.visit_file(&file);
    let mut macros = MacroCollector {
        path,
        records: Vec::new(),
    };
    macros.visit_file(&file);
    functions.records.extend(macros.records);
    functions.records.sort();
    Ok(functions.records)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> Vec<Record> {
        analyze_source(
            "calibration.rs",
            include_str!("../tests/fixtures/calibration.rs"),
        )
        .expect("fixture parses")
    }

    fn classes(function: &str) -> Vec<(String, &'static str)> {
        fixture()
            .into_iter()
            .filter(|record| record.function == function)
            .map(|record| (record.class, record.disposition))
            .collect()
    }

    fn assert_has(function: &str, class: &str, disposition: &'static str) {
        assert!(
            classes(function)
                .iter()
                .any(|actual| actual == &(class.to_owned(), disposition)),
            "missing {disposition}/{class} for {function}: {:?}",
            classes(function)
        );
    }

    fn assert_no_candidate(function: &str) {
        assert!(
            classes(function)
                .iter()
                .all(|(_, disposition)| *disposition != "candidate"),
            "unexpected candidate for {function}: {:?}",
            classes(function)
        );
    }

    #[test]
    fn recognizes_sequential_unsigned_saturating_recurrence() {
        assert_eq!(
            classes("sequential_unsigned"),
            vec![("sequential_unsigned_saturating_add".to_owned(), "candidate")]
        );
    }

    #[test]
    fn exact_manual_multilane_remains_semantically_unresolved() {
        assert_eq!(
            classes("manual_lanes"),
            vec![("manual_multilane_role_unresolved".to_owned(), "unresolved")]
        );
    }

    #[test]
    fn excludes_non_recurrence_and_constant_induction() {
        assert_eq!(
            classes("address_math"),
            vec![("non_recurrence_saturating_add".to_owned(), "excluded")]
        );
        assert_eq!(
            classes("constant_induction"),
            vec![(
                "constant_or_induction_saturating_accumulation".to_owned(),
                "excluded"
            )]
        );
    }

    #[test]
    fn separates_signed_from_unsigned_candidates() {
        assert_eq!(
            classes("signed_is_not_a_law_candidate"),
            vec![(
                "known_nonassociative_signed_saturating_add".to_owned(),
                "excluded"
            )]
        );
    }

    #[test]
    fn unresolved_shapes_are_never_candidates() {
        assert_eq!(
            classes("source_type_unresolved"),
            vec![(
                "sequential_accumulator_type_unresolved".to_owned(),
                "unresolved"
            )]
        );
        assert_eq!(
            classes("manual_without_merge"),
            vec![("manual_multilane_merge_unresolved".to_owned(), "unresolved")]
        );
        assert_eq!(
            classes("fold_needs_semantic_resolution"),
            vec![("fold_method_semantics_unresolved".to_owned(), "unresolved")]
        );
    }

    #[test]
    fn only_source_spelled_primitive_scalar_bindings_can_be_candidates() {
        for function in [
            "indexed_array_accumulator",
            "struct_field_accumulator",
            "custom_method_accumulator",
        ] {
            assert_no_candidate(function);
        }
        assert_has(
            "indexed_array_accumulator",
            "sequential_non_scalar_accumulator_unresolved",
            "unresolved",
        );
        assert_has(
            "struct_field_accumulator",
            "sequential_non_scalar_accumulator_unresolved",
            "unresolved",
        );
        assert_has(
            "custom_method_accumulator",
            "sequential_accumulator_type_unresolved",
            "unresolved",
        );
    }

    #[test]
    fn macro_code_is_an_explicit_unresolved_bucket() {
        assert!(fixture().iter().any(|record| {
            record.function == "<macro>"
                && record.class == "macro_tokens_unresolved"
                && record.disposition == "unresolved"
        }));
    }

    #[test]
    fn rejects_loop_and_body_binding_shadows() {
        assert_has(
            "shadowed_accumulator",
            "sequential_binding_shadowed",
            "unresolved",
        );
        assert_has(
            "body_binding_shadows_accumulator",
            "loop_body_binding_shadow",
            "unresolved",
        );
        assert_no_candidate("shadowed_accumulator");
        assert_no_candidate("body_binding_shadows_accumulator");
    }

    #[test]
    fn rejects_resets_macros_calls_escapes_and_other_writes() {
        for (function, class) in [
            ("reset_inside_loop", "loop_body_other_write"),
            ("macro_inside_loop", "loop_body_opaque_macro"),
            ("opaque_call_inside_loop", "loop_body_opaque_call"),
            ("escaped_accumulator", "loop_body_accumulator_escape"),
            ("other_write_inside_loop", "loop_body_other_write"),
        ] {
            assert_has(function, class, "unresolved");
            assert_no_candidate(function);
        }
    }

    #[test]
    fn requires_structural_item_derivation_and_no_opaque_transform() {
        assert_has(
            "name_mention_is_not_item_derivation",
            "constant_or_induction_saturating_accumulation",
            "excluded",
        );
        assert_has(
            "called_item_transform_is_opaque",
            "loop_body_opaque_call",
            "unresolved",
        );
        assert_no_candidate("name_mention_is_not_item_derivation");
        assert_no_candidate("called_item_transform_is_opaque");
    }

    #[test]
    fn requires_post_loop_read_before_overwrite() {
        assert_eq!(
            classes("overwritten_before_observation"),
            vec![("post_loop_accumulator_overwritten".to_owned(), "excluded")]
        );
    }

    #[test]
    fn reaching_definition_must_still_be_the_zero_initializer() {
        for function in [
            "preloop_write_replaces_initializer",
            "prior_recurrence_replaces_initializer",
            "preloop_nested_shadow_is_unproved",
        ] {
            assert_has(
                function,
                "sequential_reaching_definition_unresolved",
                "unresolved",
            );
            assert_no_candidate(function);
        }
    }

    #[test]
    fn iterable_expression_cannot_replace_the_zero_initializer() {
        assert_has(
            "iterable_expression_mutates_accumulator",
            "sequential_reaching_definition_unresolved",
            "unresolved",
        );
        assert_no_candidate("iterable_expression_mutates_accumulator");
    }

    #[test]
    fn overloaded_deref_is_not_a_source_only_item_projection() {
        assert_has(
            "overloaded_deref_operand",
            "sequential_item_projection_unresolved",
            "unresolved",
        );
        assert_no_candidate("overloaded_deref_operand");
    }

    #[test]
    fn overloaded_index_is_not_a_source_only_item_projection() {
        assert_has(
            "overloaded_index_operand",
            "sequential_item_projection_unresolved",
            "unresolved",
        );
        assert_no_candidate("overloaded_index_operand");
    }

    #[test]
    fn post_loop_destructuring_assignment_methods_escapes_and_macros_fail_closed() {
        for function in [
            "destructuring_shadow_before_observation",
            "tuple_assignment_before_observation",
            "method_mutation_before_observation",
            "mutable_escape_before_observation",
            "macro_reset_before_observation",
        ] {
            assert_has(function, "post_loop_accumulator_overwritten", "excluded");
            assert_no_candidate(function);
        }
    }

    #[test]
    fn keeps_multiple_statistics_out_of_candidate_counts() {
        assert_has(
            "multiple_statistics",
            "manual_multilane_role_unresolved",
            "unresolved",
        );
        assert_no_candidate("multiple_statistics");
    }

    #[test]
    fn every_manual_multilane_record_is_unresolved_at_stage_one() {
        assert!(fixture().iter().all(|record| {
            !record.class.starts_with("manual_multilane_") || record.disposition == "unresolved"
        }));
    }

    #[test]
    fn merge_requires_each_leaf_exactly_once() {
        assert_has(
            "duplicate_merge_leaf",
            "manual_multilane_merge_unresolved",
            "unresolved",
        );
        assert_no_candidate("duplicate_merge_leaf");
    }

    #[test]
    fn aggregate_root_use_conflicts_with_indexed_lanes() {
        assert_has(
            "whole_array_used_before_merge",
            "manual_multilane_merge_unresolved",
            "unresolved",
        );
        assert_no_candidate("whole_array_used_before_merge");
    }

    #[test]
    fn destructuring_shadow_blocks_manual_merge() {
        for function in [
            "destructuring_shadow_before_manual_merge",
            "macro_reset_before_manual_merge",
        ] {
            assert_has(function, "manual_multilane_merge_unresolved", "unresolved");
            assert_no_candidate(function);
        }
    }

    #[test]
    fn nested_functions_and_closures_are_not_attributed_to_outer_function() {
        assert!(classes("outer_does_not_own_nested_hits").is_empty());
        assert_eq!(
            classes("outer_does_not_own_nested_hits::nested"),
            vec![("sequential_unsigned_saturating_add".to_owned(), "candidate")]
        );
        assert_eq!(
            classes("closure_is_a_separate_unresolved_boundary::<closure>"),
            vec![("closure_body_unresolved".to_owned(), "unresolved")]
        );
        assert!(classes("closure_is_a_separate_unresolved_boundary")
            .iter()
            .all(|(_, disposition)| *disposition != "candidate"));
    }

    #[test]
    fn json_is_one_object_with_schema() {
        let json = fixture()[0].to_json();
        assert!(json.starts_with("{\"schema\":1,"));
        assert!(json.ends_with('}'));
    }
}
