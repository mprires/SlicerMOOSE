import shutil
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget
import slicer.util
import os
import multiprocessing
import glob
import time


multiprocessing.set_start_method("spawn", force=True)

class MOOSEExtension(ScriptedLoadableModule):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent.title = "MOOSE Extension"
        self.parent.categories = ["Segmentation"]
        self.parent.contributors = ["Manuel Pires"]
        self.parent.helpText = """
        This extension integrates the MOOSE segmentation tool into 3D Slicer for multi-organ PET/CT segmentation.
        """
        self.parent.acknowledgementText = """
        Developed as part of the ENHANCE-PET project.
        """


class MOOSEExtensionWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        super().setup()

        # Load the UI file
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MOOSEExtension.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.ui.inputSelector.setMRMLScene(slicer.mrmlScene)  # Ensure the scene is connected
        self.ui.runButton.connect('clicked()', self.onRunButtonClicked)
        self.originalInputPath = None

        self.logic = MOOSELogic()
        self.logic.logCallback = self.addLog

    def updateRunButtonState(self):
        """Enable the Run button only if inputs are valid."""
        self.ui.runButton.enabled = (
            self.ui.inputSelector.currentNode() is not None and os.path.isdir(self.ui.outputDirectoryButton.directory)
        )

    def getOriginalInputPath(self, inputNode):
        if not self.originalInputPath:
            storageNode = inputNode.GetStorageNode()
            if not storageNode or not storageNode.GetFileName():
                raise ValueError("Input volume does not have an associated file on disk.")
            self.originalInputPath = storageNode.GetFileName()  # Cache the original path

    def addLog(self, text):
        self.ui.statusLabel.appendPlainText(text)
        slicer.app.processEvents()  # force update

    def onRunButtonClicked(self):
        start = time.time()

        self.ui.statusLabel.plainText = ''
        inputNode = self.ui.inputSelector.currentNode()
        outputDirectory = self.ui.outputDirectoryButton.directory
        models = self.ui.modelsSelector.currentText.split(",")

        if not inputNode or not outputDirectory:
            slicer.util.errorDisplay("Please select an input volume and output directory.")
            return

        self.getOriginalInputPath(inputNode)
        self.logic.runSegmentation(self.originalInputPath, models, inputNode)
        

class MOOSELogic:
    def __init__(self):
        self.logCallback = None

    def runSegmentation(self, inputPath, models, inputNode):
        """
        Run MOOSE segmentation using the moosez CLI with the required folder structure.

        Args:
            inputNode (vtkMRMLScalarVolumeNode): The input volume node.
            models (list): List of models to use for segmentation.
            mainFolder (str): Path to the main folder where subject folders are stored.
            subjectID (str): ID of the subject folder.
        """
        try:
            # Set up folders and get file paths
            mainFolder, subjectFolder = self.setupFolders(inputPath, inputNode)
            self.log(f"Saved input NIfTI")
            slicer_python = shutil.which("PythonSlicer")
            self.log(slicer_python)
            # Run moosez CLI for each model
            self.log(models)
            for model in models:
                self.log(f"Running moosez for model: {model}")
                cmd = [slicer_python, "-m", "moosez", "--main_directory", mainFolder, "--model_names", model, "--verbose_off", "--logging_off"]
                result = slicer.util.launchConsoleProcess(cmd)
                self.logProcessOutput(result)
                self.log("FINISHED MOOSE")
            expectedOutputPath = glob.glob(os.path.join(subjectFolder,"moosez-*", "segmentations", "*.nii.gz"))[0]

            if not os.path.exists(expectedOutputPath):
                raise FileNotFoundError(f"Segmentation file not found: {expectedOutputPath}")

            slicer.util.loadSegmentation(expectedOutputPath)
            cleanup(mainFolder)
            slicer.util.delayDisplay(f"MOOSE segmentation completed successfully! 🚀 Segmentation loaded from: {expectedOutputPath}", 3000)

        except Exception as e:
            slicer.util.errorDisplay(f"Error during MOOSE segmentation: {e}")

    def log(self, text):
        if self.logCallback:
            self.logCallback(text)

    def logProcessOutput(self, proc, returnOutput=False):
        # Wait for the process to end and forward output to the log
        output = ""
        from subprocess import CalledProcessError
        while True:
            try:
                line = proc.stdout.readline()
                if not line:
                    break
                if returnOutput:
                    output += line
                self.log(line.rstrip())
            except UnicodeDecodeError as e:
                # Code page conversion happens because `universal_newlines=True` sets process output to text mode,
                # and it fails because probably system locale is not UTF8. We just ignore the error and discard the string,
                # as we only guarantee correct behavior if an UTF8 locale is used.
                pass

        proc.wait()
        retcode = proc.returncode
        if retcode != 0:
            raise CalledProcessError(retcode, proc.args, output=proc.stdout, stderr=proc.stderr)
        return output if returnOutput else None

    def setupFolders(self, inputpath, inputNode):
        """
        Set up the folder structure for moosez based on the original input file location.

        Args:
            inputNode (vtkMRMLScalarVolumeNode): The input volume node.

        Returns:
            tuple: Paths for:
                - mainFolder (str): Main folder derived from the CT file directory.
                - subjectFolder (str): Path to the subject folder where input NIfTI is stored.
        """
        # Define the main folder and subject folder
        mainFolder = os.path.join(os.path.dirname(inputpath), "temp")
        subjectFolder = os.path.join(mainFolder, "sub_to_moose")

        # Clear and recreate the temporary folder
        if os.path.exists(mainFolder):
            shutil.rmtree(mainFolder)

        os.makedirs(subjectFolder, exist_ok=True)
        inputNiftiPath = os.path.join(subjectFolder, "CT_sub_to_moose.nii.gz")
        slicer.util.saveNode(inputNode, inputNiftiPath)

        return mainFolder, subjectFolder


def cleanup(folderPath):
    """
    Remove the temporary folder and its contents.

    Args:
        folderPath (str): Path to the temporary folder to be removed.
    """
    if os.path.exists(folderPath):
        try:
            shutil.rmtree(folderPath)
        except Exception as cleanupError:
            slicer.util.errorDisplay(f"Failed to clean up temporary folder '{folderPath}': {cleanupError}")
