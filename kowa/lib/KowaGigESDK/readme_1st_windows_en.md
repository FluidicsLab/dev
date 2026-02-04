Kowa GigE SDK \
for Windows


# Overview

Kowa GigE SDK is Software Development Kit for GigE camera supplied by Kowa Optronics Co., Ltd.
It contains the Driver software, Library, Sample Code, Viewer Software, Setting Tools and Manuals needed to use the Kowa Optronics Co., Ltd camera on Windows.

# Supporting OS

* Windows 10 (64bit), Windows 11 (64bit)

# Install And Usage

* SDK and Library

  Run setup.exe to install SDK, library, sample programs and tools.

* Sample Program
  * CPP_ConsoleDemo_Windows(C++ sample code)
    * This is a Console Demo written in C++ that can be run in VisualStudio 2019 or later.
  * CS_ConsoleDemo_Windows(C# sample code)
    * This is a Console Demo written in C# that can be run in VisualStudio 2019 or later.
  * CS_GigeCameraCtrlSample(C# sample code)
    * This is a GUI Demo written in C# that can be run for Windows Form on VisualStudio 2019 or later.
  * CPP_RemoteFocusConsoleDemo_Windows(C++ sample code)
    * This is a Console Demo for RemoteFocus Control in C++ that can be run in VisualStudio 2019 or later.
    * This sample code uses opencv. Please set the environment variable 'OPENCV_DIR'.

* Tools
  * Kowa GigE Vision Viewer
    * Run "KowaGigEVisionViewer.exe" to execute Kowa GigE Vision Viewer.
  * IPConfigTool
    * Run "IPConfigTool.exe" to execute IPConfigTool.
    * See "IPConfigtool_gui_Manual_en.pdf" for details on how to use IPConfigTool.

* Python Wrapper
  * Install the `kge-*.whl` wheel package to your python runtime.
    The wheel package located in `%KOWA_GEV_ROOT%\Wrappers\Python\dist` (`C:\Program Files\Kowa\Optronics\Wrappers\Python\dist`).

    Execute `import kge` from python to you can use this module that .
    On the command line, `python -m kge` will run the demo script.
    Opencv and Numpy are required to run the demo script.

    Please refer to sample code to learn about the steps involved in acquiring images from the camera and how to access the camera.
    Sample code can be found in /Wrapper/Python/samples.
    See "Documents/KowaGigESDK_python" for more details about API commands.

# Requirement

* Python 3.9 or later (If you want to use with Python-Wrapper)
* OpenCV 4.5.1 or later (Required only demo script running)
* NumPy 1.19.5 or later (Required only demo script running)

# License

Library uses the following 3rd party software packages.

|Package    |License|URL                                    |
|:---       |:---   |:---                                   |
|Mathparser |LGPL   |http://kirya.narod.ru/mathparser.html  |
|libxml2    |MIT    |http://www.xmlsoft.org                 |
|libxslt    |MIT    |http://www.xmlsoft.org                 |
