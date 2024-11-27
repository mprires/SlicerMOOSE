import unittest
import slicer
from MOOSEExtension import MOOSELogic

class MOOSEExtensionTest(unittest.TestCase):
    def test_run_segmentation(self):
        """Test the MOOSE segmentation logic."""
        inputVolumeNode = slicer.util.getNode('SampleInputVolume')
        outputLabelNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
        
        logic = MOOSELogic()
        result = logic.runSegmentation(inputVolumeNode, outputLabelNode)
        
        self.assertIsNotNone(result)
        slicer.util.delayDisplay("MOOSE segmentation test passed!")

