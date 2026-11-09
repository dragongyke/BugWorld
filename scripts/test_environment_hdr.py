"""The water reflection probe must retain radiance above display white through KTX packing."""
import hashlib, tempfile, unittest
from pathlib import Path
import numpy as np
import assets_v3_environment as environment

class HdrProbeTest(unittest.TestCase):
    def test_hdr_energy_survives_writer_and_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'probe.ktx';source=hashlib.sha256(b'controlled HDR probe').hexdigest()
            levels=[np.full((6,environment.SIZE>>i,environment.SIZE>>i,3),8.,np.float32) for i in range(environment.LEVELS)]
            sh=environment.diffuse_sh(levels[0])
            environment.write_ktx(path,levels,sh,source,source_range='HDR scene-linear Blender probe')
            report=environment.validate(path,source,max_linear=None)
            self.assertEqual(report['mips'][0]['linearMax'],8.)
            np.testing.assert_allclose(report['diffuseSH'][0],[8,8,8],atol=1e-5)

if __name__=='__main__': unittest.main()
