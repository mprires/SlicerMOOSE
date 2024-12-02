import shutil
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget, ScriptedLoadableModuleTest
import slicer.util
from PyQt5 import QtGui
import os
import glob


class MOOSE(ScriptedLoadableModule):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent.title = "MOOSE"
        self.parent.categories = ["Segmentation"]
        self.parent.contributors = ["Manuel Pires, Sebastian Gutschmayer"]
        self.parent.helpText = """
        This extension integrates the MOOSE segmentation tool into 3D Slicer for multi-organ PET/CT segmentation.
        """
        self.parent.acknowledgementText = """
        Developed as part of the ENHANCE-PET project.
        """


class MOOSEWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        super().setup()

        # Load the UI file
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MOOSE.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.ui.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)  # Ensure the scene is connected
        self.ui.runButton.connect('clicked()', self.onRunButtonClicked)
        self.ui.buttonInstallDependencies.connect('clicked()', self.onbuttonInstallDependenciesClicked)

        self.logic = MOOSELogic()
        self.logic.logCallback = self.addLog

    def onbuttonInstallDependenciesClicked(self):
        try:
            import moosez
        except ModuleNotFoundError as e:
            self.ui.buttonInstallDependencies.setEnabled(False)
            self.addLog("Installing MOOSE.")
            slicer.util.pip_install("moosez")
            return
        self.ui.buttonInstallDependencies.setEnabled(False)
        self.addLog("MOOSE is already installed.")

    def addLog(self, text):
        if not text:
            return

        current_text = self.ui.statusLabel.toPlainText()
        lines = current_text.split('\n') if current_text else []

        if lines:
            last_line = lines[-1]

            if len(last_line) > 1 and len(text) > 1:
                if text.startswith(("└", "│", "┏", "┃", "┡")):
                    return

                last_line_sub = last_line[1:]
                new_text_sub = text[1:]

                if new_text_sub.startswith(("└", "│", "┏", "┃", "┡")):
                    return

                if last_line_sub.startswith((" [", "  [", " Initiating")) and new_text_sub.startswith((" [", "  [", " Initiating")):
                    lines[-1] = text
                    new_text = '\n'.join(lines)
                    self.ui.statusLabel.setPlainText(new_text)

                    cursor = self.ui.statusLabel.textCursor()
                    cursor.movePosition(QtGui.QTextCursor.End)
                    self.ui.statusLabel.setTextCursor(cursor)
                    slicer.app.processEvents()
                    return

        self.ui.statusLabel.appendPlainText(text)
        slicer.app.processEvents()

    def onRunButtonClicked(self):
        self.ui.runButton.setEnabled(False)
        self.addLog('Starting MOOSE Segmentation.')

        inputNode = self.ui.inputVolumeSelector.currentNode()
        outputDirectory = self.ui.outputDirectoryButton.directory
        models = self.ui.modelsSelector.currentText.split(",")
        if not inputNode or not outputDirectory:
            slicer.util.errorDisplay("Please select an input volume and output directory.")
            return

        moose_folder, subject_folder = self.logic.prepare_data(self.ui.inputVolumeSelector.currentNode())
        self.logic.runSegmentation(moose_folder, subject_folder, models)
        self.ui.runButton.setEnabled(True)
        self.addLog('MOOSE completed all tasks.')
        shutil.rmtree(moose_folder)


class MOOSELogic:
    def __init__(self):
        self.logCallback = None

    def runSegmentation(self, moose_folder, subject_folder, models):
        """
        Run MOOSE segmentation using the moosez CLI with the required folder structure.

        Args:
            models (list): List of models to use for segmentation.
            mainFolder (str): Path to the main folder where subject folders are stored.
            subjectID (str): ID of the subject folder.
        """
        try:
            slicer_python = shutil.which("PythonSlicer")
            for model in models:
                self.log(f"Running moosez for model: {model}")
                cmd = [slicer_python, "-m", "moosez", "--main_directory", moose_folder, "--model_names", model]
                result = slicer.util.launchConsoleProcess(cmd)
                self.logProcessOutput(result)

                label_indices = self.get_label_indices(model)

            expectedOutputPath = glob.glob(os.path.join(subject_folder, "moosez-*", "segmentations", "*.nii.gz"))[0]

            if not os.path.exists(expectedOutputPath):
                raise FileNotFoundError(f"Segmentation file not found: {expectedOutputPath}")

        except Exception as e:
            slicer.util.errorDisplay(f"Error during MOOSE segmentation: {e}")

        segmentationNode = slicer.util.loadSegmentation(expectedOutputPath)
        segmentation = segmentationNode.GetSegmentation()
        for segmentIndex in range(segmentation.GetNumberOfSegments()):
            segmentID = segmentation.GetNthSegmentID(segmentIndex)
            segmentID_numeric = int(segmentID.replace("Segment_", ""))
            segment = segmentation.GetSegment(segmentID)
            newName = label_indices[segmentID_numeric]
            segment.SetName(newName)

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

    def prepare_data(self, inputVolume):
        moose_folder = slicer.util.tempDirectory()
        subject_folder = os.path.join(moose_folder, "MOOSE_subject")
        inputFile = os.path.join(subject_folder, "CT_MOOSE_input.nii")

        volumeStorageNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLVolumeArchetypeStorageNode")
        volumeStorageNode.SetFileName(inputFile)
        volumeStorageNode.UseCompressionOff()
        volumeStorageNode.WriteData(inputVolume)
        volumeStorageNode.UnRegister(None)

        return moose_folder, subject_folder

    def get_label_indices(self, model_identifier):
        from moosez.models import Model
        from moosez.system import OutputManager
        model = Model(model_identifier, OutputManager(False, False))
        return model.organ_indices


class MOOSETest(ScriptedLoadableModuleTest):
    def setUp(self):
        """Reset the Slicer environment to ensure a clean state for testing."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run all test cases."""
        self.setUp()
        self.test_MOOSEIntegration()

    def test_MOOSEIntegration(self):
        """Test MOOSE functionality."""
        self.delayDisplay("Starting MOOSE Integration Test")

        # Load a sample volume (replace with the actual path or use Slicer sample data)
        #sampleVolume = "/media/kylo-ren/6ED4-1166/Manuel/MOOSEv2_data/sub1/clin_CT_organs_segmentation_CT_2_ac_ct_thoabd_uld_22__hd_fov.nii.gz"
        import SampleData
        sampleVolume = SampleData.downloadSample('CTChest')
        self.delayDisplay('Loaded test data set')
        self.assertIsNotNone(sampleVolume, "Failed to load sample volume")
        print("######################################################")
        print("Volume Loaded successfully")

        # Set up MOOSE logic
        mooseLogic = MOOSELogic()
        self.assertIsNotNone(mooseLogic, "MOOSELogic instance could not be created")
        print("######################################################")
        print("MOOSELogic created successfully")

        # Prepare data
        self.delayDisplay("Preparing data for segmentation")
        moose_folder, subject_folder = mooseLogic.prepare_data(sampleVolume)
        self.assertTrue(os.path.exists(moose_folder), "Temporary folder for MOOSE not created")
        print("######################################################")
        print("Data prepared successfully")

        # Run segmentation with a test model
        model = ["clin_ct_organs"]
        try:
            self.delayDisplay(f"Running segmentation for {model}")
            mooseLogic.runSegmentation(moose_folder, subject_folder, model)
        except Exception as e:
            self.fail(f"Segmentation for model {model} failed with exception: {str(e)}")
        print("######################################################")
        print(f"Infered model {model} successfully")

        # Clean up
        import shutil
        shutil.rmtree(moose_folder)
        self.delayDisplay("MOOSE test passed!")
        print("######################################################")
        print("MOOSE test passed")
