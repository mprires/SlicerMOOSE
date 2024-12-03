import shutil
import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget, ScriptedLoadableModuleTest
import slicer.util
import os
import glob
from pathlib import Path
import requests
import sysconfig
import re


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
        self.ui.buttonRunSegmentation.connect('clicked()', self.onbuttonRunSegmentationClicked)
        self.ui.buttonInstallDependencies.connect('clicked()', self.onbuttonInstallDependenciesClicked)
        self.set_gui(True)

        self.logic = MOOSELogic()
        self.logic.logCallback = self.addLog

    def set_gui(self, enabled: bool = True):
        self.ui.inputVolumeSelector.setEnabled(enabled and self.dependencies_installed())
        self.ui.buttonRunSegmentation.setEnabled(enabled and self.dependencies_installed())
        self.ui.modelsSelector.setEnabled(enabled and self.dependencies_installed())
        self.ui.buttonInstallDependencies.setEnabled(enabled and (not self.dependencies_installed()))
        slicer.app.processEvents()

    def dependencies_installed(self) -> bool:
        try:
            if os.name == "nt":
                import torch
            from moosez import moose
        except ModuleNotFoundError as e:
            return False
        return True

    def onbuttonInstallDependenciesClicked(self):
        self.set_gui(False)
        if self.dependencies_installed():
            self.addLog("Dependencies already installed.")
        else:
            self.addLog("Installing dependencies...")
            if os.name == "nt":
                slicer.util.pip_install("torch")
            slicer.util.pip_install("git+https://github.com/Keyn34/MOOSE.git")
            self.addLog("Dependencies installed successfully.")
        self.set_gui(True)

    def onbuttonRunSegmentationClicked(self):
        self.set_gui(False)

        inputNode = self.ui.inputVolumeSelector.currentNode()
        model = self.ui.modelsSelector.currentText
        if not inputNode or not model:
            slicer.util.errorDisplay("Please select an input volume and model.")
            self.set_gui(True)
            return

        self.addLog('Starting MOOSE segmentation.')
        moose_folder, subject_folder = self.logic.prepare_data(self.ui.inputVolumeSelector.currentNode())
        status_message = self.logic.run_segmentation(moose_folder, subject_folder, model)
        self.addLog(status_message)
        shutil.rmtree(moose_folder)
        self.set_gui(True)

    def remove_emojis(self, text: str) -> str:
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # Emoticons
            u"\U0001F300-\U0001F5FF"  # Symbols & Pictographs
            u"\U0001F680-\U0001F6FF"  # Transport & Map Symbols
            u"\U0001F700-\U0001F77F"  # Alchemical Symbols
            u"\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            u"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            u"\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
            u"\U0001FA00-\U0001FA6F"  # Chess Symbols
            u"\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
            u"\U00002700-\U000027BF"  # Dingbats
            u"\U0001F1E6-\U0001F1FF"  # Flags
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)

    def addLog(self, text):
        if not text:
            return

        text = self.remove_emojis(text)

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
                    self.ui.statusLabel.setPlainText(new_text.strip())
                    scrollbar = self.ui.statusLabel.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum)
                    slicer.app.processEvents()
                    return

        self.ui.statusLabel.appendPlainText(text.strip())
        slicer.app.processEvents()


class MOOSELogic:
    def __init__(self):
        self.logCallback = None
        self.moosez = os.path.join(sysconfig.get_path('scripts'), self.format_executable_name("moosez"))
        self.python = shutil.which("PythonSlicer")

    @staticmethod
    def format_executable_name(executable_name: str):
        return executable_name + ".exe" if os.name == "nt" else executable_name

    def run_segmentation(self, moose_folder, subject_folder, model) -> str:
        """
        Run MOOSE segmentation using the moosez CLI with the required folder structure.

        Args:
            moose_folder (str): List of models to use for segmentation.
            subject_folder (str): Path to the main folder where subject folders are stored.
            model (str): ID of the subject folder.
        """
        try:
            self.log(f"Running moosez for model: {model}")
            cmd = [self.python, self.moosez, "--main_directory", moose_folder, "--model_names", model]
            result = slicer.util.launchConsoleProcess(cmd)
            self.logProcessOutput(result)

            label_indices = self.get_label_indices(model)
            expectedOutputPath = glob.glob(os.path.join(subject_folder, "moosez-*", "segmentations", "*.nii.gz"))[0]

            if not os.path.exists(expectedOutputPath):
                raise FileNotFoundError(f"Segmentation file not found: {expectedOutputPath}")

            segmentationNode = slicer.util.loadSegmentation(expectedOutputPath)
            segmentation = segmentationNode.GetSegmentation()
            for segmentIndex in range(segmentation.GetNumberOfSegments()):
                segmentID = segmentation.GetNthSegmentID(segmentIndex)
                segmentID_numeric = int(segmentID.replace("Segment_", ""))
                segment = segmentation.GetSegment(segmentID)
                newName = label_indices[segmentID_numeric]
                segment.SetName(newName)

            return "MOOSE segmentation completed successfully."

        except Exception as e:
            slicer.util.errorDisplay(f"Error during MOOSE segmentation: {e}")
            return f"Error during MOOSE segmentation: {e}"

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

        sampleVolume_path = self.download_sample_data()
        sampleVolume = slicer.util.loadVolume(sampleVolume_path)

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


        # Run segmentation with a test model
        test_models = ["clin_ct_cardiac", "clin_ct_muscles", "clin_ct_organs", "clin_ct_peripheral_bones",
                       "clin_ct_ribs", "clin_ct_vertebrae"]
        for model in test_models:
            try:
                self.delayDisplay("Preparing data for segmentation")
                moose_folder, subject_folder = mooseLogic.prepare_data(sampleVolume)
                self.assertTrue(os.path.exists(moose_folder), "Temporary folder for MOOSE not created")
                print("######################################################")
                print("Data prepared successfully")
                self.delayDisplay(f"Running segmentation for {model}")
                mooseLogic.run_segmentation(moose_folder, subject_folder, model)
            except Exception as e:
                self.fail(f"Segmentation for model {model} failed with exception: {str(e)}")
            print("######################################################")
            print(f"Infered model {model} successfully")

        # Clean up
            import shutil
            shutil.rmtree(moose_folder)
        os.remove(sampleVolume_path)
        self.delayDisplay("MOOSE test passed!")
        print("######################################################")
        print("MOOSE test passed")

    def download_sample_data(self):

        download_directory = self.get_default_download_folder()
        URL = "https://enhance-pet.s3.eu-central-1.amazonaws.com/slicer_sample_data/sample_CT.nii.gz"
        download_file_name = os.path.basename(URL)
        download_file_path = os.path.join(download_directory, download_file_name)

        response = requests.get(URL, stream=True)
        if response.status_code != 200:
            output_manager.console_update(f"    X Failed to download model from {URL}")
            raise Exception(f"Failed to download model from {URL}")
        chunk_size = 1024 * 10

        with open(download_file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
        return download_file_path


    def get_default_download_folder(self):
        if os.name == 'nt':  # For Windows
            download_folder = Path(os.getenv('USERPROFILE')) / 'Downloads'
        else:  # For macOS and Linux
            download_folder = Path.home() / 'Downloads'

        return download_folder
