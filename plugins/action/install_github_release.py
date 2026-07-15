from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import time
import shutil
import tempfile
from ansible.plugins.action import ActionBase
from ansible.module_utils.urls import open_url

# Nothing else prunes ~/.ansible/cache/github_releases, so sweep entries older than this on every run.
CACHE_MAX_AGE = 30 * 86400


class ActionModule(ActionBase):
    def _prune_cache(self, cache_dir):
        try:
            entries = os.listdir(cache_dir)
        except OSError:
            return
        now = time.time()
        for entry in entries:
            path = os.path.join(cache_dir, entry)
            try:
                if now - os.path.getmtime(path) > CACHE_MAX_AGE:
                    os.remove(path)
            except OSError:
                pass

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        module_args = self._task.args.copy()

        repo = module_args.get("repo")
        if not repo:
            return {"failed": True, "msg": "repo is required"}

        tag = module_args.get("tag", "latest")

        # Determine cache dir on control node
        cache_dir = os.path.expanduser("~/.ansible/cache/github_releases")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        self._prune_cache(cache_dir)

        release_cache_file = os.path.join(cache_dir, f"release_{repo.replace('/', '_')}_{tag}.json")

        release_info = None
        # Cache release info for 10 minutes (600 seconds)
        if os.path.exists(release_cache_file) and (time.time() - os.path.getmtime(release_cache_file)) < 600:
            try:
                with open(release_cache_file, "r") as f:
                    release_info = json.load(f)
            except Exception:
                pass

        if not release_info:
            if tag == "latest":
                url = f"https://api.github.com/repos/{repo}/releases/latest"
            else:
                url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"

            headers = {}
            if "GITHUB_TOKEN" in os.environ:
                headers["Authorization"] = "token " + os.environ["GITHUB_TOKEN"]

            try:
                response = open_url(url, headers=headers)
                release_info = json.loads(response.read().decode('utf-8'))
                with open(release_cache_file, "w") as f:
                    json.dump(release_info, f)
            except Exception as e:
                return {"failed": True, "msg": f"Failed to fetch release info from {url}. Rate limit or network issue? Details: {str(e)}"}

        # Run module in 'check' mode to see if installation is needed and retrieve selected asset url
        check_args = module_args.copy()
        check_args["github_release_info"] = release_info
        check_args["action_step"] = "check"

        check_result = self._execute_module(
            module_name='astappiev.common.install_github_release',
            module_args=check_args,
            task_vars=task_vars
        )

        if check_result.get("failed"):
            check_result["msg"] = f"Module failed in check mode: {check_result.get('msg', 'no message')}"
            return check_result

        if not check_result.get("needs_install"):
            return check_result

        if self._task.check_mode:
            return check_result

        # Installation is needed
        selected_asset = check_result.get("selected_asset")
        if not selected_asset:
            return {"failed": True, "msg": f"Module requested install but did not provide selected_asset. check_result: {str(check_result)}"}

        asset_url = selected_asset["url"]
        asset_name = selected_asset["name"]

        # Download asset to control node cache. Key by tag (not just file name) so a new
        # release whose asset name doesn't embed the version doesn't serve a stale binary.
        repo_clean = repo.replace('/', '_')
        tag_clean = str(release_info.get("tag_name", tag)).replace('/', '_')
        asset_cache_file = os.path.join(cache_dir, f"asset_{repo_clean}_{tag_clean}_{asset_name}")

        # Cache the downloaded binary for 3 days (259200 seconds)
        if not os.path.exists(asset_cache_file) or (time.time() - os.path.getmtime(asset_cache_file)) > 259200:
            try:
                headers = {}
                if "GITHUB_TOKEN" in os.environ:
                    headers["Authorization"] = "token " + os.environ["GITHUB_TOKEN"]

                # Download to a uniquely-named temp file so concurrent hosts installing the
                # same asset don't interleave writes into the same path before the rename.
                fd, temp_asset_path = tempfile.mkstemp(dir=cache_dir, prefix=f"asset_{repo_clean}_{tag_clean}_", suffix=".tmp")
                try:
                    response = open_url(asset_url, headers=headers)
                    with os.fdopen(fd, "wb") as f:
                        shutil.copyfileobj(response, f)
                    os.rename(temp_asset_path, asset_cache_file)
                except Exception:
                    if os.path.exists(temp_asset_path):
                        os.remove(temp_asset_path)
                    raise
            except Exception as e:
                return {"failed": True, "msg": f"Failed to download asset {asset_url} to {asset_cache_file}: {str(e)}"}

        # Ensure the file exists before proceeding
        if not os.path.exists(asset_cache_file):
            return {"failed": True, "msg": f"Asset file {asset_cache_file} disappeared after download or was never created."}

        # Transfer the asset to the remote node
        remote_tmp = self._make_tmp_path()
        remote_tmp_file = self._connection._shell.join_path(remote_tmp, asset_name)

        try:
            self._transfer_file(asset_cache_file, remote_tmp_file)
            self._fixup_perms2((remote_tmp, remote_tmp_file))
        except Exception as e:
            return {"failed": True, "msg": f"Failed to transfer asset to remote node: {str(e)}"}

        # Run module in 'install' mode
        install_args = module_args.copy()
        install_args["github_release_info"] = release_info
        install_args["local_archive_path"] = remote_tmp_file
        install_args["action_step"] = "install"

        install_result = self._execute_module(
            module_name='astappiev.common.install_github_release',
            module_args=install_args,
            task_vars=task_vars
        )

        # Cleanup remote tmp directory
        self._execute_module(
            module_name='ansible.builtin.file',
            module_args={'path': remote_tmp, 'state': 'absent'},
            task_vars=task_vars
        )

        return install_result
