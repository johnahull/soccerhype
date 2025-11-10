# Third-Party Licenses

SoccerHype uses several open-source libraries and tools. This document acknowledges these dependencies and their licenses.

## Table of Contents

- [Runtime Dependencies](#runtime-dependencies)
  - [FFmpeg](#ffmpeg)
  - [Python Packages](#python-packages)
- [Development Dependencies](#development-dependencies)
- [Bundled Software](#bundled-software)
- [License Compatibility](#license-compatibility)

---

## Runtime Dependencies

### FFmpeg

**Project**: FFmpeg - A complete, cross-platform solution to record, convert and stream audio and video
**Website**: https://ffmpeg.org/
**License**: LGPL v2.1+ or GPL v2+ (depending on build configuration)
**Used for**: Video processing, codec conversion, overlay rendering

**License Information**:

FFmpeg is licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later. However, if FFmpeg is built with certain features or codecs, it may be licensed under the GNU General Public License (GPL) version 2 or later.

**Important Note**: SoccerHype does **not** bundle or distribute FFmpeg. Users must install FFmpeg separately on their system. The standalone application packages may optionally bundle FFmpeg - see the [Bundled Software](#bundled-software) section.

**FFmpeg License Text**: https://ffmpeg.org/legal.html

**GPL/LGPL Compliance**:
- SoccerHype interfaces with FFmpeg as a separate process via subprocess calls
- No FFmpeg source code is included in SoccerHype
- SoccerHype's MIT license is compatible with LGPL when using FFmpeg as a separate process
- Users who bundle GPL-licensed FFmpeg builds should be aware of GPL obligations

---

### Python Packages

#### OpenCV (opencv-python)

**Project**: OpenCV - Open Source Computer Vision Library
**Website**: https://opencv.org/
**License**: Apache License 2.0
**Used for**: Image processing, video frame manipulation (in mark_play.py)

```
Copyright (C) 2000-2024, Intel Corporation, all rights reserved.
Copyright (C) 2009-2011, Willow Garage Inc., all rights reserved.
Copyright (C) 2009-2016, NVIDIA Corporation, all rights reserved.
Copyright (C) 2010-2013, Advanced Micro Devices, Inc., all rights reserved.
Copyright (C) 2015-2016, OpenCV Foundation, all rights reserved.
Copyright (C) 2015-2016, Itseez Inc., all rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

**Full License**: https://github.com/opencv/opencv/blob/master/LICENSE

---

#### Pillow (PIL Fork)

**Project**: Pillow - Python Imaging Library
**Website**: https://python-pillow.org/
**License**: Historical Permission Notice and Disclaimer (HPND)
**Used for**: Image loading and processing for intro slates

```
The Python Imaging Library (PIL) is

    Copyright © 1997-2011 by Secret Labs AB
    Copyright © 1995-2011 by Fredrik Lundh

Pillow is the friendly PIL fork. It is

    Copyright © 2010-2024 by Jeffrey A. Clark and contributors

Like PIL, Pillow is licensed under the open source HPND License
```

**Full License**: https://github.com/python-pillow/Pillow/blob/main/LICENSE

---

#### PyYAML

**Project**: PyYAML - YAML parser and emitter for Python
**Website**: https://pyyaml.org/
**License**: MIT License
**Used for**: Configuration file parsing (optional/extended functionality)

```
Copyright (c) 2017-2021 Ingy döt Net
Copyright (c) 2006-2016 Kirill Simonov

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Full License**: https://github.com/yaml/pyyaml/blob/master/LICENSE

---

#### Tkinter

**Project**: Tkinter - Python interface to Tcl/Tk
**Website**: https://docs.python.org/3/library/tkinter.html
**License**: Python Software Foundation License
**Used for**: GUI applications (soccerhype_gui.py, reorder_clips.py)

Tkinter is part of the Python Standard Library and is licensed under the Python Software Foundation License, which is GPL-compatible and allows commercial use.

**Full License**: https://docs.python.org/3/license.html

---

## Development Dependencies

### pytest

**Project**: pytest - Python testing framework
**Website**: https://pytest.org/
**License**: MIT License
**Used for**: Unit testing and test automation

**Full License**: https://github.com/pytest-dev/pytest/blob/main/LICENSE

---

### PyInstaller

**Project**: PyInstaller - Freeze Python programs into stand-alone executables
**Website**: https://pyinstaller.org/
**License**: GPL v2 with a special exception for use with open source software
**Used for**: Creating standalone application packages

**Important Note**: PyInstaller is licensed under GPL v2 with a special exception that allows bundling with software licensed under Apache License 2.0, MIT License, and other compatible licenses. This exception applies to SoccerHype.

**PyInstaller Exception**:
```
In addition, as a special exception, the copyright holders give permission
to link the code of portions of this program with the OpenSSL library.
You must obey the GNU General Public License in all respects for all of
the code used other than OpenSSL. If you modify this file, you may extend
this exception to your version of the file, but you are not obligated to
do so. If you do not wish to do so, delete this exception statement from
your version.
```

**Full License**: https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

---

## Bundled Software

### Standalone Application Packages

When distributed as a standalone application (Windows .exe or macOS .app), SoccerHype may bundle:

1. **Python Runtime**: Python Software Foundation License
2. **Python Libraries**: Licenses as listed above
3. **FFmpeg (Optional)**: LGPL v2.1+ or GPL v2+ (see FFmpeg section above)

**Note**: The bundling of FFmpeg is optional. If FFmpeg is bundled with the standalone package:
- The GPL/LGPL license applies to the FFmpeg binaries
- Users redistributing the bundled package must comply with GPL/LGPL terms
- Source code for FFmpeg is available at https://ffmpeg.org/download.html
- SoccerHype itself remains MIT licensed as a separate work

---

## License Compatibility

SoccerHype is licensed under the MIT License, which is compatible with:

- ✅ **Apache License 2.0** (OpenCV)
- ✅ **HPND License** (Pillow)
- ✅ **MIT License** (PyYAML, pytest)
- ✅ **PSF License** (Python, Tkinter)
- ✅ **GPL v2 with Exception** (PyInstaller)
- ✅ **LGPL v2.1+** (FFmpeg as separate process)

### GPL Considerations

**When using FFmpeg as a separate process** (default installation):
- SoccerHype communicates with FFmpeg via subprocess calls
- No GPL contamination occurs because FFmpeg is a separate process
- SoccerHype remains MIT licensed

**When bundling GPL-licensed FFmpeg** (optional standalone packages):
- The combined work (SoccerHype + FFmpeg) may be subject to GPL
- Redistributors must comply with GPL terms for the bundled package
- SoccerHype source code remains MIT licensed
- Users can rebuild SoccerHype without FFmpeg or with LGPL-only FFmpeg

---

## Attribution

SoccerHype gratefully acknowledges the contributions of the open-source community and the maintainers of the projects listed above.

---

## Questions?

For license questions or concerns, please:
- Review the full LICENSE file in this repository
- Contact: john@johnahull.com
- Open an issue: https://github.com/johnahull/highlight_tool/issues

---

*Last updated: 2025-01-10*
