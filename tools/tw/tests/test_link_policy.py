"""本repo連結政策的正向與負向回歸；測試不寫入儲存庫。"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import link_policy as links

class LinkPolicyTests(unittest.TestCase):
    def setUp(self):self.policy=json.loads(links.read(links.CONFIG))
    def test_current_repo(self):
        report=links.audit();self.assertEqual(report['errors'],[])
        self.assertEqual(len(report['retained_upstream_links']),2)
    def test_hidden_skill_upstream_rejected(self):
        original=links.read
        def polluted(path,root=links.ROOT):
            value=original(path,root)
            if path=='.claude/skills/life-decision-guide/SKILL.md':
                value+='\nhttps://raw.githubusercontent.com/'+self.policy['upstream_repository']+'/main/skills/life-decision-guide/SKILL.md\n'
            return value
        with patch.object(links,'read',side_effect=polluted):
            with self.assertRaises(ValueError):links.audit()
    def test_encoded_upstream_detected(self):
        value='https://github.com/'+self.policy['upstream_repository'].replace('/','%2F')+'/issues/123'
        self.assertTrue(links.upstream_kind(value,self.policy))
    def test_missing_repo_file_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://github.com/'+self.policy['repository']+'/blob/main/nonexistent.html',self.policy)
    def test_directory_as_blob_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://github.com/'+self.policy['repository']+'/blob/main/tools',self.policy)
    def test_old_work_branch_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://github.com/'+self.policy['repository']+'/blob/old-work/README.md',self.policy)
    def test_nonexistent_release_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://github.com/'+self.policy['repository']+'/releases/download/unused/book.pdf',self.policy)
    def test_unpublished_site_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://'+self.policy['unpublished_site_host']+'/HowToLiveBetter-TW/',self.policy)
    def test_disabled_issues_rejected(self):
        with self.assertRaises(ValueError):links.own_target('https://github.com/'+self.policy['repository']+'/issues/new',self.policy)
    def test_raw_existing_image_allowed(self):
        result=links.own_target('https://raw.githubusercontent.com/'+self.policy['repository']+'/main/og.png',self.policy)
        self.assertEqual(result,links.ROOT/'og.png')
    def test_relative_explicit_anchor(self):
        self.assertEqual(links.local_target('REPOSITORY_GUIDE.md#exports','README.md'),links.ROOT/'REPOSITORY_GUIDE.md')
    def test_missing_anchor_rejected(self):
        with self.assertRaises(ValueError):links.local_target('REPOSITORY_GUIDE.md#does-not-exist','README.md')
    def test_relative_path_escape_rejected(self):
        with self.assertRaises(ValueError):links.local_target('../../outside.md','README.md')
    def test_valid_clone_and_pr_links(self):
        for tail in ('.git','/pulls','/pull/2'):
            links.own_target('https://github.com/'+self.policy['repository']+tail,self.policy)

if __name__=='__main__':unittest.main()
