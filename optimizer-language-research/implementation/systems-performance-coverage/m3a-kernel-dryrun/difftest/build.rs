use std::process::Command;
fn main() {
    let out = std::env::var("OUT_DIR").unwrap();
    let manifest = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let src = format!("{}/../ctable.c", manifest);
    let obj = format!("{}/ctable.o", out);
    let lib = format!("{}/libctable.a", out);
    // System cc (Apple clang via /usr/bin/cc), NOT the wasi clang in PATH.
    assert!(Command::new("/usr/bin/cc")
        .args(["-O3", "-mcpu=native", "-std=c11", "-c", &src, "-o", &obj])
        .status().unwrap().success());
    assert!(Command::new("/usr/bin/ar")
        .args(["crs", &lib, &obj]).status().unwrap().success());
    println!("cargo:rustc-link-search=native={}", out);
    println!("cargo:rustc-link-lib=static=ctable");
    println!("cargo:rerun-if-changed={}/../ctable.c", manifest);
    println!("cargo:rerun-if-changed={}/../ctable.h", manifest);
}
