import unittest
from presentation import report_html, report_script, report_css

class BrandingTests(unittest.TestCase):
    def test_remove_presentation_links_and_keep_results(self):
        html='''<head><title>Theragen Bio</title><link rel="shortcut icon" href="old.ico"></head>
        [<a href="https://www.theragenbio.com/en/support/help-desk">Contact</a>]
        <a href="https://example.org/paper">Citation</a><table><td>1.234</td></table>
        <a href="../../expression/genes.expression.xlsx">Excel</a>'''
        out=report_html(html,'genes/index.html')
        self.assertNotIn('theragen',out.lower())
        self.assertNotIn('old.ico',out)
        self.assertIn('href="/results/favicon.svg?v=2"',out)
        self.assertIn('<table><td>1.234</td></table>',out)
        self.assertIn('https://example.org/paper',out)
        self.assertIn('href="../expression/genes.expression.xlsx"',out)
        nested=report_html(html,'genes/0/gene.html')
        self.assertIn('href="../../expression/genes.expression.xlsx"',nested)

    def test_script_only_changes_header_footer_and_title(self):
        source='''function make_footer(depth) {
 var footer = 'Email bio@theragenbio.com | 1522 | Company address';
 $('#page-top').append(footer);
}
var logo = '<img src="' + depth + '../assets/img/bio/Theragen_bio_logo.png">';
var title = 'Theragen Bio';
function get_deg_side_menu() { return 'DEG001_gene.html'; }
'''
        result=report_script(source)
        self.assertNotIn('theragen',result.lower())
        self.assertNotIn('Company address',result)
        self.assertNotIn('Analysis report',result)
        self.assertNotIn('<img',result)
        self.assertIn("function get_deg_side_menu() { return 'DEG001_gene.html'; }",result)
        self.assertEqual(report_script('unrelated report script'),'unrelated report script')
        self.assertTrue(report_css('body{}').startswith('body{}'))

if __name__=='__main__':unittest.main()
