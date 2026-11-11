from pathlib import Path
import re

root = Path("whisper")
cmake = root / "CMakeLists.txt"
text = cmake.read_text()
text = re.sub(r'^\s*set\(CMAKE_C(?:XX)?_FLAGS[^\n]*-pthread[^\n]*\)\n', '\n', text, flags=re.M)
cmake.write_text(text)

wasm_cmake = root / "examples/whisper.wasm/CMakeLists.txt"
text = wasm_cmake.read_text()
if "-s USE_PTHREADS=1" not in text:
    raise RuntimeError("Whisper WASM pthread optie ontbreekt of is gewijzigd")
wasm_cmake.write_text(text.replace("-s USE_PTHREADS=1", "-s USE_PTHREADS=0"))

source = root / "examples/whisper.wasm/emscripten.cpp"
text = source.read_text()
if "std::thread g_worker;" not in text:
    raise RuntimeError("Whisper worker definitie gewijzigd")
text = text.replace("#include <thread>", "")
text = text.replace("std::thread g_worker;", "")
text, count = re.subn(r'\s*if \(g_worker\.joinable\(\)\) \{\s*g_worker\.join\(\);\s*\}', '', text)
if count != 3:
    raise RuntimeError(f"Verwacht 3 join-blokken; gevonden {count}")
text = text.replace("std::min(nthreads, std::min(16, mpow2(std::thread::hardware_concurrency())))", "1")
text = text.replace("std::thread::hardware_concurrency()", "1")
old = """g_worker = std::thread([index, params, pcmf32 = std::move(pcmf32), is_multilingual]() {
                whisper_reset_timings(g_contexts[index]);
                whisper_full(g_contexts[index], params, pcmf32.data(), pcmf32.size());
                whisper_print_timings(g_contexts[index]);
                if (is_multilingual) {
                    free((void*)params.language);
                }
            });"""
new = """whisper_reset_timings(g_contexts[index]);
            whisper_full(g_contexts[index], params, pcmf32.data(), pcmf32.size());
            whisper_print_timings(g_contexts[index]);
            if (is_multilingual) {
                free((void*)params.language);
            }"""
if old not in text:
    raise RuntimeError("Whisper worker implementatie gewijzigd")
text = text.replace(old, new)
source.write_text(text)
print("Whisper single-thread patch toegepast")
