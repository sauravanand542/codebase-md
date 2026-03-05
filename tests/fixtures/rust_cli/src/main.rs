use clap::Parser;

mod lib;

/// A minimal Rust CLI tool.
#[derive(Parser)]
#[command(name = "rust-cli", about = "A simple CLI")]
struct Cli {
    /// Name to greet
    #[arg(default_value = "World")]
    name: String,
}

fn main() {
    let cli = Cli::parse();
    println!("{}", lib::greet(&cli.name));
}
