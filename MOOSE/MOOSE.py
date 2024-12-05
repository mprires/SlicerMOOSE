import slicer
from slicer.ScriptedLoadableModule import ScriptedLoadableModule, ScriptedLoadableModuleWidget, ScriptedLoadableModuleTest
import slicer.util

import qt

import shutil
import os
import glob
from pathlib import Path
import requests
import sysconfig
import importlib.util


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

class InstallError(Exception):
    def __init__(self, message, restartRequired=False):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.message = message
        self.restartRequired = restartRequired
    def __str__(self):
        return self.message


class MOOSEWidget(ScriptedLoadableModuleWidget):
    def setup(self):
        super().setup()

        # Load the UI file
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MOOSE.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        self.ui.selector_input_volume.setMRMLScene(slicer.mrmlScene)
        self.ui.button_segmentation_run.connect('clicked()', self.button_segmentation_run_clicked)
        self.ui.button_install_dependencies.connect('clicked()', self.button_install_dependencies_clicked)
        self.ui.button_model_folder_open.connect('clicked()', self.button_model_folder_open_clicked)
        self.ui.button_model_folder_clear.connect('clicked()', self.button_model_folder_clear_clicked)
        self.ui.selector_output_volume.setMRMLScene(slicer.mrmlScene)
        self.ui.selector_output_volume.connect("currentNodeChanged(vtkMRMLNode*)", self.ui.button_segmentation_show.setSegmentationNode)

        self.update_gui(True)

        self.logic = MOOSELogic()
        self.logic.status_callback = self.update_status_panel

    def update_gui(self, enabled: bool = True):
        self.ui.selector_input_volume.setEnabled(enabled and self.dependencies_installed())
        self.ui.button_segmentation_run.setEnabled(enabled and self.dependencies_installed())
        self.ui.selector_models.setEnabled(enabled and self.dependencies_installed())
        self.ui.button_install_dependencies.setEnabled(enabled and (not self.dependencies_installed()))
        slicer.app.processEvents()

    def is_package_installed(self, package_name: str) -> bool:
        if importlib.util.find_spec(package_name) is not None:
            return True
        else:
            return False

    def install_pytorch(self):
        if os.name == 'nt':
            if not self.is_package_installed('PyTorchUtils'):
                raise InstallError("This module requires PyTorch extension. Install it from the Extensions Manager.")

            import PyTorchUtils
            minimumTorchVersion = "1.12"
            torchLogic = PyTorchUtils.PyTorchUtilsLogic()

            if not torchLogic.torchInstalled():
                self.update_status_panel('PyTorch Python package is required. Installing... (it may take several minutes)')
                torch = torchLogic.installTorch(askConfirmation=True, torchVersionRequirement=f">={minimumTorchVersion}")
                if torch is None:
                    raise InstallError("This module requires PyTorch extension. Install it from the Extensions Manager.")
            else:
                from packaging import version
                if version.parse(torchLogic.torch.__version__) < version.parse(minimumTorchVersion):
                    raise InstallError(
                        f'PyTorch version {torchLogic.torch.__version__} is not compatible with this module.'
                        + f' Minimum required version is {minimumTorchVersion}. You can use "PyTorch Util" module to install PyTorch'
                        + f' with version requirement set to: >={minimumTorchVersion}')

        else:
            self.update_status_panel('PyTorch Python package is required. Installing... (it may take several minutes)')
            slicer.util.pip_install("torch")

    def dependencies_installed(self) -> bool:
        if not self.is_package_installed("torch"):
            return False

        if not self.is_package_installed("moosez"):
            return False

        return True

    def button_install_dependencies_clicked(self):
        self.update_gui(False)
        if self.dependencies_installed():
            self.update_status_panel("Dependencies already installed.")
        else:
            self.update_status_panel("Installing dependencies...")
            self.install_pytorch()
            slicer.util.pip_install("git+https://github.com/Keyn34/MOOSE.git@SlicerMOOSE")
            self.update_status_panel("Dependencies installed successfully.")
        self.update_gui(True)

    def button_segmentation_run_clicked(self):
        self.update_gui(False)

        inputNode = self.ui.selector_input_volume.currentNode()
        model = self.ui.selector_models.currentText
        if not inputNode or not model:
            slicer.util.errorDisplay("Please select an input volume and model.")
            self.update_gui(True)
            return

        self.update_status_panel('Starting MOOSE segmentation.')
        moose_folder, subject_folder = self.logic.prepare_data(self.ui.selector_input_volume.currentNode())
        segmentation_file = self.logic.run_segmentation(moose_folder, subject_folder, model)

        segmentationNode = slicer.util.loadSegmentation(segmentation_file)
        self.ui.selector_output_volume.setCurrentNode(segmentationNode)
        segmentation = segmentationNode.GetSegmentation()
        label_indices = self.logic.get_label_indices(model)
        for segmentIndex in range(segmentation.GetNumberOfSegments()):
            segmentID = segmentation.GetNthSegmentID(segmentIndex)
            segmentID_numeric = int(segmentID.replace("Segment_", ""))
            segment = segmentation.GetSegment(segmentID)
            newName = label_indices[segmentID_numeric]
            segment.SetName(newName)

        shutil.rmtree(moose_folder)
        self.update_gui(True)

    def button_model_folder_open_clicked(self):
        if not os.path.exists(self.logic.models_directory):
            os.makedirs(self.logic.models_directory)
        qt.QDesktopServices().openUrl(qt.QUrl.fromLocalFile(self.logic.models_directory))

    def button_model_folder_clear_clicked(self):
        if not os.path.exists(self.logic.models_directory):
            slicer.util.messageBox("There are no downloaded models.")
            return
        if not slicer.util.confirmOkCancelDisplay("All downloaded model files will be deleted. The files will be automatically downloaded again as needed."):
            return
        self.logic.clear_models_directory_path()
        slicer.util.messageBox("Downloaded models are deleted.")

    def update_status_panel(self, text):
        if not text:
            return

        current_text = self.ui.text_edit_status_panel.toPlainText()
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
                    self.ui.text_edit_status_panel.setPlainText(new_text)
                    scrollbar = self.ui.text_edit_status_panel.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum)
                    slicer.app.processEvents()
                    return

        self.ui.text_edit_status_panel.appendPlainText(text)
        slicer.app.processEvents()


class MOOSELogic:
    def __init__(self):
        self.status_callback = None
        python_real = shutil.which("python-real")
        self.models_directory = os.path.join(os.path.dirname(python_real), 'models', 'nnunet_trained_models')
        self.moosez = os.path.join(sysconfig.get_path('scripts'), self.format_executable_name("moosez"))
        self.python_slicer = shutil.which("PythonSlicer")

    @staticmethod
    def format_executable_name(executable_name: str):
        return executable_name + ".exe" if os.name == "nt" else executable_name

    def run_segmentation(self, moose_folder: str, subject_folder: str, model: str) -> str:
        try:
            self.forward_status(f"Running moosez for model: {model}")
            cmd = [self.python_slicer, self.moosez, "--main_directory", moose_folder, "--model_names", model]
            result = slicer.util.launchConsoleProcess(cmd)
            self.forward_process_status(result)
            expectedOutputPath = glob.glob(os.path.join(subject_folder, "moosez-*", "segmentations", "*.nii.gz"))[0]

            if not os.path.exists(expectedOutputPath):
                raise FileNotFoundError(f"Segmentation file not found: {expectedOutputPath}")

            return expectedOutputPath

        except Exception as e:
            slicer.util.errorDisplay(f"Error during MOOSE segmentation: {e}")

    def prepare_data(self, inputVolume):
        self.forward_status(f"Preparing data...")
        moose_folder = slicer.util.tempDirectory()
        subject_folder = os.path.join(moose_folder, "MOOSE_subject")
        inputFile = os.path.join(subject_folder, "CT_MOOSE_input.nii")

        volumeStorageNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLVolumeArchetypeStorageNode")
        volumeStorageNode.SetFileName(inputFile)
        volumeStorageNode.UseCompressionOff()
        volumeStorageNode.WriteData(inputVolume)
        volumeStorageNode.UnRegister(None)

        return moose_folder, subject_folder

    def clear_models_directory_path(self):
        if os.path.exists(self.models_directory):
            shutil.rmtree(self.models_directory)
            self.forward_status(f"Model directory cleared.")

    def get_label_indices(self, model_identifier):
        from moosez.models import Model
        from moosez.system import OutputManager
        model = Model(model_identifier, OutputManager(False, False), self.models_directory)
        return model.organ_indices

    def forward_status(self, text):
        if self.status_callback:
            self.status_callback(text)

    def forward_process_status(self, proc, returnOutput=False):
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
                self.forward_status(line.rstrip())
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
