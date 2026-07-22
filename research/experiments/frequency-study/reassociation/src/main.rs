use reassociation_source_miner::{analyze_source, Record};
use std::env;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

fn rust_files(path: &Path, out: &mut Vec<PathBuf>) -> io::Result<()> {
    if path.is_file() {
        if path.extension().is_some_and(|ext| ext == "rs") {
            out.push(path.to_path_buf());
        }
        return Ok(());
    }
    if !path.is_dir() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            format!("input does not exist: {}", path.display()),
        ));
    }
    let mut entries = fs::read_dir(path)?.collect::<Result<Vec<_>, _>>()?;
    entries.sort_by_key(|entry| entry.file_name());
    for entry in entries {
        let child = entry.path();
        let name = entry.file_name();
        if child.is_dir() && (name == "target" || name == ".git") {
            continue;
        }
        rust_files(&child, out)?;
    }
    Ok(())
}

fn failure_record(path: &str, class: &str, reason: String) -> Record {
    Record {
        path: path.to_owned(),
        line: 1,
        column: 1,
        function: "<file>".to_owned(),
        disposition: "unresolved",
        class: class.to_owned(),
        law_requirement: "unknown",
        reason,
    }
}

fn main() {
    let inputs: Vec<_> = env::args_os().skip(1).map(PathBuf::from).collect();
    if inputs.is_empty() {
        eprintln!("usage: reassociation-source-miner <file-or-directory> [...]");
        std::process::exit(2);
    }

    let mut files = Vec::new();
    let mut records = Vec::new();
    let mut incomplete = false;
    for input in inputs {
        if let Err(error) = rust_files(&input, &mut files) {
            incomplete = true;
            records.push(failure_record(
                &input.display().to_string(),
                "input_io_error",
                error.to_string(),
            ));
        }
    }
    files.sort();
    files.dedup();
    if files.is_empty() {
        incomplete = true;
        records.push(failure_record(
            "<inputs>",
            "no_rust_files",
            "no .rs files were found in the supplied inputs".to_owned(),
        ));
    }

    for file in files {
        let display = file.display().to_string();
        match fs::read_to_string(&file) {
            Ok(source) => match analyze_source(&display, &source) {
                Ok(mut found) => records.append(&mut found),
                Err(error) => {
                    incomplete = true;
                    records.push(failure_record(&display, "file_parse_error", error));
                }
            },
            Err(error) => {
                incomplete = true;
                records.push(failure_record(
                    &display,
                    "input_io_error",
                    error.to_string(),
                ));
            }
        }
    }

    records.sort();
    for record in records {
        println!("{}", record.to_json());
    }
    if incomplete {
        std::process::exit(2);
    }
}
