import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Set
from app.models.schemas import Component

class DependencyParser:
    @staticmethod
    def parse_repository(repo_path: Path) -> List[Component]:
        """
        Walks the repository and extracts all components from supported manifests.
        Deduplicates by ecosystem + name + version, marking as direct if any manifest declared it directly.
        """
        components: Dict[str, Component] = {}
        
        # 1. Python manifests
        for req_file in repo_path.glob("**/requirements*.txt"):
            if "node_modules" in req_file.parts or ".venv" in req_file.parts:
                continue
            DependencyParser._parse_requirements_txt(req_file, repo_path, components)
            
        for pyproject in repo_path.glob("**/pyproject.toml"):
            if "node_modules" in pyproject.parts or ".venv" in pyproject.parts:
                continue
            DependencyParser._parse_pyproject_toml(pyproject, repo_path, components)
            
        for poetry_lock in repo_path.glob("**/poetry.lock"):
            if "node_modules" in poetry_lock.parts or ".venv" in poetry_lock.parts:
                continue
            DependencyParser._parse_poetry_lock(poetry_lock, repo_path, components)

        # 2. JavaScript / TypeScript manifests
        for pkg_lock in repo_path.glob("**/package-lock.json"):
            if "node_modules" in pkg_lock.parts:
                continue
            DependencyParser._parse_package_lock_json(pkg_lock, repo_path, components)
            
        for pkg_json in repo_path.glob("**/package.json"):
            if "node_modules" in pkg_json.parts:
                continue
            DependencyParser._parse_package_json(pkg_json, repo_path, components)

        # 3. Go manifests
        for go_mod in repo_path.glob("**/go.mod"):
            if "vendor" in go_mod.parts:
                continue
            DependencyParser._parse_go_mod(go_mod, repo_path, components)

        # 4. Java Maven pom.xml
        for pom_xml in repo_path.glob("**/pom.xml"):
            if "target" in pom_xml.parts:
                continue
            DependencyParser._parse_pom_xml(pom_xml, repo_path, components)

        return list(components.values())

    @staticmethod
    def _parse_requirements_txt(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Match name and version pinned e.g. requests==2.19.1 or urllib3>=1.24
                m = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([a-zA-Z0-9_\-\.]+)", line)
                if m:
                    name = m.group(1).lower()
                    version = m.group(2)
                    key = f"pypi:{name}:{version}"
                    purl = f"pkg:pypi/{name}@{version}"
                    components[key] = Component(
                        name=name,
                        version=version,
                        ecosystem="pypi",
                        purl=purl,
                        direct=True,
                        manifest_path=rel_path,
                        license="Unknown"
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_pyproject_toml(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            in_deps = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("[") and ("dependencies" in line.lower() or "tool.poetry.dependencies" in line.lower()):
                    in_deps = True
                    continue
                elif line.startswith("["):
                    in_deps = False
                    continue
                
                if in_deps and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip().strip('"').strip("'").lower()
                    val = parts[1].strip().strip('"').strip("'")
                    v_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", val)
                    version = v_match.group(1) if v_match else "0.0.0"
                    if name and name != "python":
                        key = f"pypi:{name}:{version}"
                        components[key] = Component(
                            name=name,
                            version=version,
                            ecosystem="pypi",
                            purl=f"pkg:pypi/{name}@{version}",
                            direct=True,
                            manifest_path=rel_path
                        )
        except Exception:
            pass

    @staticmethod
    def _parse_poetry_lock(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            curr_name = ""
            curr_version = ""
            for line in content.splitlines():
                line = line.strip()
                if line == "[[package]]":
                    if curr_name and curr_version:
                        key = f"pypi:{curr_name}:{curr_version}"
                        if key not in components:
                            components[key] = Component(
                                name=curr_name,
                                version=curr_version,
                                ecosystem="pypi",
                                purl=f"pkg:pypi/{curr_name}@{curr_version}",
                                direct=False,
                                manifest_path=rel_path
                            )
                    curr_name = ""
                    curr_version = ""
                elif line.startswith("name = "):
                    curr_name = line.split("=", 1)[1].strip().strip('"').lower()
                elif line.startswith("version = "):
                    curr_version = line.split("=", 1)[1].strip().strip('"')
            
            if curr_name and curr_version:
                key = f"pypi:{curr_name}:{curr_version}"
                if key not in components:
                    components[key] = Component(
                        name=curr_name,
                        version=curr_version,
                        ecosystem="pypi",
                        purl=f"pkg:pypi/{curr_name}@{curr_version}",
                        direct=False,
                        manifest_path=rel_path
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_package_json(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
            all_deps = {}
            if "dependencies" in data and isinstance(data["dependencies"], dict):
                all_deps.update(data["dependencies"])
            if "devDependencies" in data and isinstance(data["devDependencies"], dict):
                all_deps.update(data["devDependencies"])
                
            for name, ver_spec in all_deps.items():
                clean_ver = re.sub(r"[^0-9\.]", "", str(ver_spec).split("-")[0])
                if not clean_ver:
                    clean_ver = "1.0.0"
                key = f"npm:{name.lower()}:{clean_ver}"
                # If already discovered via lockfile, mark direct
                if key in components:
                    components[key].direct = True
                else:
                    components[key] = Component(
                        name=name.lower(),
                        version=clean_ver,
                        ecosystem="npm",
                        purl=f"pkg:npm/{name.lower()}@{clean_ver}",
                        direct=True,
                        manifest_path=rel_path
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_package_lock_json(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
            # npm lockfile v2 / v3
            if "packages" in data and isinstance(data["packages"], dict):
                for pkg_key, pkg_info in data["packages"].items():
                    if not pkg_key:  # root package
                        continue
                    name = pkg_info.get("name")
                    if not name:
                        # "node_modules/lodash" -> "lodash"
                        parts = pkg_key.split("node_modules/")
                        name = parts[-1] if len(parts) > 1 else pkg_key
                    version = pkg_info.get("version", "0.0.0")
                    is_dev = pkg_info.get("dev", False)
                    # Node modules depth determines if direct
                    is_direct = pkg_key.count("node_modules/") == 1
                    
                    key = f"npm:{name.lower()}:{version}"
                    components[key] = Component(
                        name=name.lower(),
                        version=version,
                        ecosystem="npm",
                        purl=f"pkg:npm/{name.lower()}@{version}",
                        direct=is_direct,
                        manifest_path=rel_path,
                        license=pkg_info.get("license", "Unknown")
                    )
            # npm lockfile v1 fallback
            elif "dependencies" in data and isinstance(data["dependencies"], dict):
                for name, dep_info in data["dependencies"].items():
                    ver = dep_info.get("version", "0.0.0")
                    key = f"npm:{name.lower()}:{ver}"
                    components[key] = Component(
                        name=name.lower(),
                        version=ver,
                        ecosystem="npm",
                        purl=f"pkg:npm/{name.lower()}@{ver}",
                        direct=True,
                        manifest_path=rel_path
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_go_mod(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            in_require = False
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("require ("):
                    in_require = True
                    continue
                elif line == ")" and in_require:
                    in_require = False
                    continue
                
                parts = line.split()
                if in_require and len(parts) >= 2:
                    name = parts[0]
                    ver = parts[1].lstrip("v")
                    is_direct = "// indirect" not in line
                    key = f"golang:{name}:{ver}"
                    components[key] = Component(
                        name=name,
                        version=ver,
                        ecosystem="golang",
                        purl=f"pkg:golang/{name}@{ver}",
                        direct=is_direct,
                        manifest_path=rel_path
                    )
                elif line.startswith("require ") and len(parts) >= 3:
                    name = parts[1]
                    ver = parts[2].lstrip("v")
                    is_direct = "// indirect" not in line
                    key = f"golang:{name}:{ver}"
                    components[key] = Component(
                        name=name,
                        version=ver,
                        ecosystem="golang",
                        purl=f"pkg:golang/{name}@{ver}",
                        direct=is_direct,
                        manifest_path=rel_path
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_pom_xml(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            # Handle XML namespaces
            ns = {"m": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
            prefix = "m:" if ns else ""
            
            for dep in root.findall(f".//{prefix}dependency", ns):
                g = dep.find(f"{prefix}groupId", ns)
                a = dep.find(f"{prefix}artifactId", ns)
                v = dep.find(f"{prefix}version", ns)
                if g is not None and a is not None:
                    group_id = g.text.strip() if g.text else ""
                    art_id = a.text.strip() if a.text else ""
                    ver = v.text.strip() if v is not None and v.text else "unknown"
                    full_name = f"{group_id}:{art_id}"
                    key = f"maven:{full_name}:{ver}"
                    components[key] = Component(
                        name=full_name,
                        version=ver,
                        ecosystem="maven",
                        purl=f"pkg:maven/{group_id}/{art_id}@{ver}",
                        direct=True,
                        manifest_path=rel_path
                    )
        except Exception:
            pass

