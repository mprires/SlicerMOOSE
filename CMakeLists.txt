cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SlicerMOOSE)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/mprires/SlicerMOOSE")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Manuel Pires (QIMP Vienna), Sebastian Gutschmayer (QIMP Vienna)")
set(EXTENSION_DESCRIPTION "The 3DSlicer Extensions for MOOSE: (Multi-organ objective segmentation) is a data-centric AI solution that generates multilabel organ segmentations to facilitate systemic TB whole-person research. The extension, the MOOSE package, and segmentation models are distributed under the GPL license.")
set(EXTENSION_ICONURL "https://github.com/mprires/SlicerMOOSE/raw/main/MOOSE/Resources/Icons/MOOSE.png")
set(EXTENSION_SCREENSHOTURLS "https://github.com/mprires/SlicerMOOSE/raw/main/Images/SlicerMOOSE_Screenshot1.png")
set(EXTENSION_DEPENDS "PyTorch") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(MOOSE)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
