import shutil

import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget
import os
import slicer.util
import multiprocessing
import subprocess
import glob
from pathlib import Path

multiprocessing.set_start_method("spawn", force=True)

class MOOSEExtension(ScriptedLoadableModule):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent.title = "MOOSE Extension"
        self.parent.categories = ["Segmentation"]
        self.parent.contributors = ["Lalith Kumar Shiyam Sundar, PhD"]
        self.parent.helpText = """
        This extension integrates the MOOSE segmentation tool into 3D Slicer for multi-organ PET/CT segmentation.
        """
        self.parent.acknowledgementText = """
        Developed as part of the ENHANCE-PET project.
        """

class MOOSEExtensionWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        super().setup()
        
        nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode")
        for i in range(nodes.GetNumberOfItems()):
            print("Available node:", nodes.GetItemAsObject(i).GetName())
        # Load the UI file
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MOOSEExtension.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.ui.inputSelector.setMRMLScene(slicer.mrmlScene)  # Ensure the scene is connected
        self.ui.runButton.connect('clicked()', self.onRunButtonClicked)

    def updateRunButtonState(self):
        """Enable the Run button only if inputs are valid."""
        self.ui.runButton.enabled = (
            self.ui.inputSelector.currentNode() is not None and
            os.path.isdir(self.ui.outputDirectoryButton.directory)
        )

    def onRunButtonClicked(self):
        """Run the segmentation."""
        inputNode = self.ui.inputSelector.currentNode()
        outputDirectory = self.ui.outputDirectoryButton.directory
        models = self.ui.modelsSelector.currentText.split(",")  # Assume user can select multiple models
        accelerator = 'cuda' if self.ui.useCudaCheckbox.checked else 'cpu'

        if not inputNode or not outputDirectory:
            slicer.util.errorDisplay("Please select an input volume and output directory.")
            return

        logic = MOOSELogic()
        logic.runSegmentation(inputNode, models, accelerator)
        

class MOOSELogic:
    def runSegmentation(self, inputNode, models, accelerator='cuda'):
        """
        Run MOOSE segmentation using the moosez CLI with the required folder structure.

        Args:
            inputNode (vtkMRMLScalarVolumeNode): The input volume node.
            models (list): List of models to use for segmentation.
            mainFolder (str): Path to the main folder where subject folders are stored.
            subjectID (str): ID of the subject folder.
            accelerator (str): 'cuda' or 'cpu' for GPU or CPU acceleration.
        """
        try:
            # Set up folders and get file paths
            mainFolder, subjectFolder = setupFolders(inputNode)
            print(f"Saved input NIfTI")
            slicer_python = shutil.which("PythonSlicer")
            print(slicer_python)
            # Run moosez CLI for each model
            for model in models:
                print(f"Running moosez for model: {model}")
                cmd = [
                    "/home/kylo-ren/Downloads/Slicer-5.6.1-linux-amd64/slicer.org/Extensions-32438/MOOSEExtension/run_moose.sh",
                    "--main_directory", mainFolder,
                    "--model_names", model
                ]

                # Call the CLI
                result = slicer.util.launchConsoleProcess(cmd)
                output = slicer.util.logProcessOutput(result)
                print("FINISHED MOOSE")
            print(os.path.join(subjectFolder,"moosez-*", "segmentations", "*.nii.gz"))
            expectedOutputPath = glob.glob(os.path.join(subjectFolder,"moosez-*", "segmentations", "*.nii.gz"))[0]
            # Validate and load the segmentation file
            if not os.path.exists(expectedOutputPath):
                raise FileNotFoundError(f"Segmentation file not found: {expectedOutputPath}")

            slicer.util.loadSegmentation(expectedOutputPath)
            slicer.util.delayDisplay(f"MOOSE segmentation completed successfully! 🚀 Segmentation loaded from: {expectedOutputPath}", 3000)

        except Exception as e:
            slicer.util.errorDisplay(f"Error during MOOSE segmentation: {e}")

    @staticmethod
    def convertVolumeNodeToNumpy(volumeNode):
        """
        Convert a Slicer volume node to a NumPy array and extract its spacing.

        Args:
            volumeNode (vtkMRMLScalarVolumeNode): Input volume node.

        Returns:
            tuple: A tuple containing:
                - numpyArray (np.ndarray): The voxel data as a NumPy array.
                - spacing (tuple): The voxel spacing as a tuple (x, y, z).
        """
        if not volumeNode:
            raise ValueError("Invalid volume node: None")

        # Convert the volume node's voxel data to a NumPy array
        numpyArray = slicer.util.arrayFromVolume(volumeNode)

        # Get the voxel spacing from the volume node
        spacing = volumeNode.GetSpacing()

        return numpyArray, spacing

    @staticmethod
    def loadSegmentationIntoSlicer(segmentation_file_path):
        """
        Loads a segmentation result file into Slicer as a segmentation node.

        Args:
            segmentation_file_path: Path to the segmentation file.
        """
        if not os.path.exists(segmentation_file_path):
            raise FileNotFoundError(f"Segmentation file not found: {segmentation_file_path}")

        # Load segmentation into Slicer
        segmentation_node = slicer.util.loadSegmentation(segmentation_file_path)
        if segmentation_node:
            slicer.util.delayDisplay("Segmentation loaded into Slicer.")
        else:
            raise RuntimeError("Failed to load segmentation into Slicer.")


def setupFolders(inputNode):
    """
    Set up the folder structure for moosez based on the input CT file location.

    Args:
        inputNode (vtkMRMLScalarVolumeNode): The input volume node.
        subjectID (str): ID of the subject folder.

    Returns:
        tuple: Paths for:
            - mainFolder (str): Main folder derived from the CT file directory.
            - inputNiftiPath (str): Path to save the input NIfTI file.
            - expectedOutputPath (str): Path where the segmentation file will be saved.
    """
    # Get the directory of the input CT file
    storageNode = inputNode.GetStorageNode()
    if not storageNode or not storageNode.GetFileName():
        raise ValueError("Input volume does not have an associated file on disk.")

    inputFilePath = storageNode.GetFileName()
    print(inputFilePath)
    mainFolder = os.path.join(os.path.dirname(inputFilePath), "temp")
    # Create the subject folder
    subjectFolder = os.path.join(mainFolder, "sub_to_moose")
    if not os.path.exists(subjectFolder):
        os.makedirs(subjectFolder)
        print(f"Created subject folder: {subjectFolder}")

    # Path for the input NIfTI file
    inputNiftiPath = os.path.join(subjectFolder, f"CT_sub_to_moose.nii.gz")

    slicer.util.saveNode(inputNode, inputNiftiPath)
    return mainFolder, subjectFolder
