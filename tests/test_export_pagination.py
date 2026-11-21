import unittest
from io import BytesIO
import tempfile
from pptx import Presentation
from backend.quick_reading.export import ExportDocument, ExportSection, _export_pptx

class ExportPaginationTests(unittest.TestCase):
    def test_long_section_is_split_without_losing_end_marker(self):
        content = '长篇技术内容' * 600 + ' END-OF-REPORT'
        doc = ExportDocument('test.pdf','Long report',[], '', '', '', [ExportSection('技术细节', paragraphs=[content])])
        with tempfile.TemporaryDirectory() as root:
            result=_export_pptx(doc, root, root+'/cache')
        self.assertEqual(result.status,200)
        prs=Presentation(BytesIO(result.payload['data']))
        self.assertGreater(len(prs.slides),3)
        text=''.join(shape.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame)
        self.assertIn('END-OF-REPORT',text)
        for slide in prs.slides:
            for shape in slide.shapes:
                self.assertLessEqual(shape.top+shape.height,prs.slide_height)
