import datetime
import json
import tempfile
import unittest

from unittest.mock import patch

from genny.cedar_report import CertRetriever, main__cedar_report
from tests.cedar_test import get_fixture


class _NoopCertRetriever(CertRetriever):
    @staticmethod
    def _fetch(url, output, **kwargs):
        return output


_FIXED_DATETIME = datetime.datetime(year=2000, month=1, day=1).isoformat()


class CedarReportTest(unittest.TestCase):

    @patch('genny.cedar_report.ShellCuratorRunner.run')
    def test_cedar_report(self, mock_uploader_run):
        """
        This test documents the environment variables needed to run cedar_report.py and checks that
        the environment variables are correctly used.
        """
        mock_env = {
            'EVG_task_name': 'my_task_name',
            'EVG_project': 'my_project',
            'EVG_version': 'my_version',
            'EVG_variant': 'my_variant',
            'EVG_task_id': 'my_task_id',
            'EVG_execution_number': 'my_execution_number',
            'EVG_is_patch': 'true',  # This should get converted to mainline = False in the report.

            'test_name': 'my_test_name',

            'perf_jira_user': 'my_username',
            'perf_jira_pw': 'my_password',

            'aws_key': 'my_aws_key',
            'aws_secret': 'my_aws_secret'
        }

        expected_uploader_run_args = [
            'curator', 'poplar', 'send', '--service', 'cedar.mongodb.com:7070', '--cert',
            'cedar.user.crt', '--key', 'cedar.user.key', '--ca', 'cedar.ca.pem', '--path',
            'cedar_report.json']

        expected_json = {
            'project': 'my_project',
            'version': 'my_version',
            'variant': 'my_variant',
            'task_name': 'my_task_name',
            'task_id': 'my_task_id',
            'execution_number': 'my_execution_number',
            'mainline': False,
            'tests': [{
                'info': {
                    'test_name': 'my_task_name',
                    'trial': 0,
                    'tags': [],
                    'args': {}
                },
                'created_at': _FIXED_DATETIME,
                'completed_at': _FIXED_DATETIME,
                'artifacts': {
                    'api_key': 'my_aws_key',
                    'api_secret': 'my_aws_secret',
                    'api_token': None,
                    'region': 'us-east-1',
                    'name': 'dsi-genny-metrics',
                    'prefix': 'my_task_id_my_execution_number'
                },
                'metrics': None,
                'sub_tests': None
            }],
            'bucket': [
                'my_aws_key',
                'my_aws_secret',
                None,
                'us-east-1',
                'dsi-genny-metrics',
                'my_task_id_my_execution_number'
            ]}

        with tempfile.TemporaryDirectory() as output_dir:
            argv = [get_fixture('cedar', 'shared_with_cxx_metrics_test.csv'), output_dir]
            main__cedar_report(argv, mock_env, _NoopCertRetriever)

            with open('cedar_report.json') as f:
                report_json = json.load(f)

                # Just do a basic type check. The test time isn't used.
                datetime.datetime.fromisoformat(report_json['tests'][0]['created_at'])
                datetime.datetime.fromisoformat(report_json['tests'][0]['completed_at'])

                report_json['tests'][0]['created_at'] = _FIXED_DATETIME
                report_json['tests'][0]['completed_at'] = _FIXED_DATETIME

                self.assertDictEqual(expected_json, report_json)

        mock_uploader_run.assert_called_with(expected_uploader_run_args)
