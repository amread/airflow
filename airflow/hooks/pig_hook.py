from __future__ import print_function
import logging
import subprocess
from tempfile import NamedTemporaryFile

from airflow.utils import AirflowException
from airflow.hooks.base_hook import BaseHook
from airflow.utils import TemporaryDirectory
from airflow import configuration


class PigCliHook(BaseHook):
    """
    Simple wrapper around the pig CLI.

    Note that you can also set default pig CLI properties using the
    ``pig_properties`` to be used in your connection as in
    ``{"pig_properties": "-Dpig.tmpfilecompression=true"}``

    """

    def __init__(
            self,
            pig_cli_conn_id="pig_cli_default"):
        conn = self.get_connection(pig_cli_conn_id)
        self.pig_properties = conn.extra_dejson.get('pig_properties', '')
        self.conn = conn

    def run_cli(self, pig, verbose=True):
        """
        Run an pig script using the pig cli

        >>> ph = PigCliHook()
        >>> result = ph.run_cli("ls /;")
        >>> ("hdfs://" in result)
        True
        """

        with TemporaryDirectory(prefix='airflow_pigop_') as tmp_dir:
            with NamedTemporaryFile(dir=tmp_dir) as f:
                f.write(pig)
                f.flush()
                fname = f.name
                pig_bin = 'pig'
                cmd_extra = []

                pig_cmd = [pig_bin, '-f', fname] + cmd_extra

                if self.pig_properties:
                    pig_properties_list = self.pig_properties.split()
                    pig_cmd.extend(pig_properties_list)
                if verbose:
                    logging.info(" ".join(pig_cmd))
                sp = subprocess.Popen(
                    pig_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=tmp_dir)
                self.sp = sp
                stdout = ''
                for line in iter(sp.stdout.readline, ''):
                    stdout += line
                    if verbose:
                        logging.info(line.strip())
                sp.wait()

                if sp.returncode:
                    raise AirflowException(stdout)

                return stdout

    def kill(self):
        if hasattr(self, 'sp'):
            if self.sp.poll() is None:
                print("Killing the Hive job")
                self.sp.kill()
