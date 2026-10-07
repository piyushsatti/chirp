# Licenses and voice provenance

Chirp is licensed under **GPL-3.0-or-later**; see [LICENSE](../LICENSE). This
license was selected for compatibility with the Piper runtime. Third-party
components retain their own licenses.

## Speech engine

The selected engine is **OHF-Voice Piper 1.8.0**, whose upstream package metadata
declares `GPL-3.0-or-later`. Piper bundles eSpeak NG. Refer to the
[Piper source and license](https://github.com/OHF-Voice/piper1-gpl) and the
[GPLv3 text, including section 2](https://www.gnu.org/licenses/gpl-3.0.html#section2),
for permissions and conditions. Setup downloads the engine and its dependencies
from their upstream package sources.

## Voice

The selected voice is **en_US-ljspeech-medium**, a US English female voice at
22,050 Hz. Its ONNX model is 63,531,379 bytes (about 60.6 MiB).

The [voice repository metadata](https://huggingface.co/rhasspy/piper-voices)
declares MIT. The specific
[model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD)
states that the voice was trained from scratch on the public-domain LJ Speech
dataset. The [dataset publisher](https://keithito.com/LJ-Speech-Dataset/)
describes the recordings and transcripts as public domain in the United States.

The verified model SHA-256 is:

```text
6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22
```

## Other runtime components

| Component | Version tested | Upstream license |
| --- | --- | --- |
| sounddevice | 0.5.5 | MIT |
| PortAudio | V19.7.0 | MIT-style permissive |
| ONNX Runtime | 1.30.0 | MIT |

See the upstream [sounddevice license](https://github.com/spatialaudio/python-sounddevice/blob/master/LICENSE),
[PortAudio license](https://www.portaudio.com/license.html), and
[ONNX Runtime license](https://github.com/microsoft/onnxruntime/blob/main/LICENSE).
Transitive packages retain their upstream licenses; this table is not a complete
inventory of every dependency or bundled third-party notice.
