from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import json
import time
import urllib.request
from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError

class ActionModule(ActionBase):
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
            
            try:
                req = urllib.request.Request(url)
                if "GITHUB_TOKEN" in os.environ:
                    req.add_header("Authorization", "token " + os.environ["GITHUB_TOKEN"])
                with urllib.request.urlopen(req) as response:
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
            return check_result
            
        if not check_result.get("needs_install"):
            return check_result
            
        if self._task.check_mode:
            return check_result
            
        # Installation is needed
        selected_asset = check_result.get("selected_asset")
        if not selected_asset:
            return {"failed": True, "msg": "Module requested install but did not provide selected_asset."}
            
        asset_url = selected_asset["url"]
        asset_name = selected_asset["name"]
        
        # Download asset to control node cache
        asset_cache_file = os.path.join(cache_dir, f"asset_{repo.replace('/', '_')}_{asset_name}")
        
        # Cache the downloaded binary for 3 days (259200 seconds)
        if not os.path.exists(asset_cache_file) or (time.time() - os.path.getmtime(asset_cache_file)) > 259200:
            try:
                urllib.request.urlretrieve(asset_url, asset_cache_file)
            except Exception as e:
                return {"failed": True, "msg": f"Failed to download asset {asset_url}: {str(e)}"}
        
        # Transfer the asset to the remote node
        remote_tmp_dir = self._connection._shell.tmpdir or self._connection._shell.get_remote_filename(self._connection.get_option('remote_tmp'))
        remote_tmp_file = self._connection._shell.join_path(remote_tmp_dir, asset_name)
        
        # We can use transfer_file or execute `copy` module
        # let's use the builtin copy module for simplicity and reliability
        copy_args = {
            "src": asset_cache_file,
            "dest": remote_tmp_file,
            "mode": "0600"
        }
        copy_result = self._execute_module(
            module_name="ansible.builtin.copy", 
            module_args=copy_args, 
            task_vars=task_vars
        )
        
        if copy_result.get("failed"):
            return copy_result
            
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
        
        # Cleanup remote tmp file
        self._execute_module(
            module_name='ansible.builtin.file',
            module_args={'path': remote_tmp_file, 'state': 'absent'},
            task_vars=task_vars
        )
        
        return install_result
