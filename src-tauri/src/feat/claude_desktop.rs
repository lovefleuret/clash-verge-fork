use crate::process::AsyncHandler;
use clash_verge_logging::{Type, logging};
use smartstring::alias::String;
use std::{path::Path, thread, time::Duration};
use tauri_plugin_clash_verge_sysinfo::sysinfo::{Pid, ProcessRefreshKind, ProcessesToUpdate, System, UpdateKind};

const GRACEFUL_TIMEOUT: Duration = Duration::from_secs(10);
const FORCE_TIMEOUT: Duration = Duration::from_secs(3);
const POLL_INTERVAL: Duration = Duration::from_millis(200);

fn is_claude_desktop(exe: &Path) -> bool {
    #[cfg(target_os = "macos")]
    {
        exe.ends_with("Claude.app/Contents/MacOS/Claude")
    }
    // Claude Code also ships a claude.exe, so match the desktop app's install folders only.
    #[cfg(windows)]
    {
        let path = exe.to_string_lossy().to_ascii_lowercase();
        path.ends_with("\\claude.exe") && (path.contains("\\anthropicclaude\\") || path.contains("\\windowsapps\\"))
    }
    #[cfg(not(any(target_os = "macos", windows)))]
    {
        let _ = exe;
        false
    }
}

fn find_claude_pids(sys: &mut System) -> Vec<Pid> {
    sys.refresh_processes_specifics(
        ProcessesToUpdate::All,
        true,
        ProcessRefreshKind::nothing().with_exe(UpdateKind::OnlyIfNotSet),
    );
    sys.processes()
        .iter()
        .filter(|(_, process)| process.exe().is_some_and(is_claude_desktop))
        .map(|(pid, _)| *pid)
        .collect()
}

fn wait_for_exit(sys: &mut System, timeout: Duration) -> Vec<Pid> {
    let mut waited = Duration::ZERO;
    loop {
        let pids = find_claude_pids(sys);
        if pids.is_empty() || waited >= timeout {
            return pids;
        }
        thread::sleep(POLL_INTERVAL);
        waited += POLL_INTERVAL;
    }
}

fn request_quit(sys: &System, pid: Pid) {
    #[cfg(unix)]
    {
        if let Some(process) = sys.process(pid) {
            process.kill_with(tauri_plugin_clash_verge_sysinfo::sysinfo::Signal::Term);
        }
    }
    // sysinfo only force-kills on Windows; taskkill without /F asks the windows to close.
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt as _;
        let _ = sys;
        let _ = std::process::Command::new("taskkill")
            .args(["/PID", &pid.to_string()])
            .creation_flags(0x0800_0000)
            .output();
    }
}

fn quit_blocking() -> Result<(), String> {
    let mut sys = System::new();
    let pids = find_claude_pids(&mut sys);
    if pids.is_empty() {
        return Ok(());
    }

    logging!(info, Type::ProxyMode, "Quitting Claude Desktop before switching to rule mode");
    for pid in pids {
        request_quit(&sys, pid);
    }
    let remaining = wait_for_exit(&mut sys, GRACEFUL_TIMEOUT);
    if remaining.is_empty() {
        return Ok(());
    }

    logging!(warn, Type::ProxyMode, "Claude Desktop did not quit in time, force killing it");
    for pid in remaining {
        if let Some(process) = sys.process(pid) {
            process.kill();
        }
    }
    if wait_for_exit(&mut sys, FORCE_TIMEOUT).is_empty() {
        Ok(())
    } else {
        Err("Claude Desktop is still running, rule mode was not applied".into())
    }
}

/// Returns only once Claude Desktop has fully exited, so the caller can safely enter rule mode.
pub async fn quit_claude_desktop() -> Result<(), String> {
    AsyncHandler::spawn_blocking(quit_blocking)
        .await
        .map_err(|err| String::from(err.to_string()))?
}
