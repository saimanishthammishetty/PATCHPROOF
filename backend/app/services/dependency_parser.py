import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional
from app.models.schemas import Component

class DependencyParser:
    @staticmethod
    def determine_scope_details(
        manifest_path: str,
        is_dev: bool = False,
        is_test: bool = False,
        group: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Determines component scope, reason, and confidence.
        Returns: (scope, reason, confidence)
          scope: 'production' | 'development' | 'test' | 'fixture' | 'unclassified'
          confidence: 'High' | 'Medium' | 'Low'
        """
        norm_path = manifest_path.replace("\\", "/").lower()
        parts = norm_path.split("/")
        filename = parts[-1]

        # 1. Fixture repositories
        if any(p in ("fixtures", "fixture", "test-fixtures") for p in parts[:-1]) or "fixture" in filename:
            return "fixture", f"Manifest located inside test fixture directory: {manifest_path}", "High"

        # 2. Test manifests and test directories
        if any(p in ("test", "tests", "__tests__", "testing", "spec", "specs") for p in parts[:-1]):
            return "test", f"Manifest located in test directory: {manifest_path}", "High"
        if is_test or any(k in filename for k in ("test-requirements", "requirements-test", "requirements_test", "test.txt")):
            return "test", f"Declared in dedicated test manifest: {manifest_path}", "High"
        if group and any(k in group.lower() for k in ("test", "tests")):
            return "test", f"Declared in test dependency group [{group}] in {manifest_path}", "High"

        # 3. Development manifests and devDependencies
        if is_dev:
            return "development", f"Declared as development dependency (devDependencies) in {manifest_path}", "High"
        if any(k in filename for k in ("dev-requirements", "requirements-dev", "requirements_dev", "dev.txt")):
            return "development", f"Declared in development requirements file: {manifest_path}", "High"
        if group and any(k in group.lower() for k in ("dev", "development", "tools", "lint")):
            return "development", f"Declared in development group [{group}] in {manifest_path}", "High"
        if any(p in ("scripts", "tools", "ci", ".github") for p in parts[:-1]):
            return "development", f"Manifest located in developer/CI tooling directory: {manifest_path}", "Medium"

        # 4. Standard production manifests
        if filename in ("requirements.txt", "package.json", "package-lock.json", "go.mod", "pom.xml", "pyproject.toml", "poetry.lock"):
            return "production", f"Declared in standard application manifest: {manifest_path}", "High"

        # 5. Non-standard or ambiguous manifests
        if filename.endswith(".txt") and not any(k in filename for k in ("prod", "production", "app")):
            return "unclassified", f"Ambiguous manifest context for {manifest_path}; handled conservatively", "Low"

        return "production", f"Identified as production dependency from {manifest_path}", "Medium"

    @staticmethod
    def determine_scope(manifest_path: str, is_dev: bool = False) -> str:
        """
        Backward-compatible helper returning scope string.
        """
        scope, _, _ = DependencyParser.determine_scope_details(manifest_path, is_dev=is_dev)
        return scope

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
            for line_idx, raw_line in enumerate(content.splitlines(), 1):
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Match name and version pinned e.g. requests==2.19.1 or urllib3>=1.24
                m = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*(?:==|>=|<=|~=)\s*([a-zA-Z0-9_\-\.]+)", line)
                if m:
                    name = m.group(1).lower()
                    version = m.group(2)
                    key = f"pypi:{name}:{version}"
                    purl = f"pkg:pypi/{name}@{version}"
                    scope, reason, conf = DependencyParser.determine_scope_details(rel_path)
                    components[key] = Component(
                        name=name,
                        version=version,
                        ecosystem="pypi",
                        purl=purl,
                        direct=True,
                        manifest_path=rel_path,
                        license="Unknown",
                        scope=scope,
                        scope_reason=reason,
                        scope_confidence=conf,
                        line_number=line_idx,
                        manifest_snippet=line
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_pyproject_toml(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            in_deps = False
            current_group = None
            for line_idx, raw_line in enumerate(content.splitlines(), 1):
                line = raw_line.strip()
                if line.startswith("["):
                    line_lower = line.lower()
                    if "tool.poetry.dev-dependencies" in line_lower or "dev" in line_lower:
                        in_deps = True
                        current_group = "dev"
                    elif "dependencies" in line_lower:
                        in_deps = True
                        current_group = "production"
                    else:
                        in_deps = False
                        current_group = None
                    continue
                
                if in_deps and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip().strip('"').strip("'").lower()
                    val = parts[1].strip().strip('"').strip("'")
                    v_match = re.search(r"(\d+\.\d+(?:\.\d+)?)", val)
                    version = v_match.group(1) if v_match else "0.0.0"
                    if name and name != "python":
                        key = f"pypi:{name}:{version}"
                        is_dev = current_group == "dev"
                        scope, reason, conf = DependencyParser.determine_scope_details(
                            rel_path, is_dev=is_dev, group=current_group
                        )
                        components[key] = Component(
                            name=name,
                            version=version,
                            ecosystem="pypi",
                            purl=f"pkg:pypi/{name}@{version}",
                            direct=True,
                            manifest_path=rel_path,
                            scope=scope,
                            scope_reason=reason,
                            scope_confidence=conf,
                            line_number=line_idx,
                            manifest_snippet=line
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
            scope, reason, conf = DependencyParser.determine_scope_details(rel_path)
            for line_idx, raw_line in enumerate(content.splitlines(), 1):
                line = raw_line.strip()
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
                                manifest_path=rel_path,
                                scope=scope,
                                scope_reason=reason,
                                scope_confidence=conf,
                                line_number=line_idx,
                                manifest_snippet=f"name = \"{curr_name}\", version = \"{curr_version}\""
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
                        manifest_path=rel_path,
                        scope=scope,
                        scope_reason=reason,
                        scope_confidence=conf
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_package_json(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(raw_text)
            lines = raw_text.splitlines()

            def find_line_info(pkg_name: str) -> Tuple[Optional[int], Optional[str]]:
                search_term = f'"{pkg_name}"'
                for idx, l in enumerate(lines, 1):
                    if search_term.lower() in l.lower():
                        return idx, l.strip()
                return None, None

            # 1. Production dependencies
            if "dependencies" in data and isinstance(data["dependencies"], dict):
                for name, ver_spec in data["dependencies"].items():
                    clean_ver = re.sub(r"[^0-9\.]", "", str(ver_spec).split("-")[0]) or "1.0.0"
                    key = f"npm:{name.lower()}:{clean_ver}"
                    line_no, snippet = find_line_info(name)
                    scope, reason, conf = DependencyParser.determine_scope_details(rel_path, is_dev=False)
                    if key in components:
                        components[key].direct = True
                        components[key].scope = scope
                        components[key].scope_reason = reason
                        components[key].scope_confidence = conf
                        if line_no:
                            components[key].line_number = line_no
                            components[key].manifest_snippet = snippet
                    else:
                        components[key] = Component(
                            name=name.lower(),
                            version=clean_ver,
                            ecosystem="npm",
                            purl=f"pkg:npm/{name.lower()}@{clean_ver}",
                            direct=True,
                            manifest_path=rel_path,
                            scope=scope,
                            scope_reason=reason,
                            scope_confidence=conf,
                            line_number=line_no,
                            manifest_snippet=snippet
                        )

            # 2. Development dependencies
            if "devDependencies" in data and isinstance(data["devDependencies"], dict):
                for name, ver_spec in data["devDependencies"].items():
                    clean_ver = re.sub(r"[^0-9\.]", "", str(ver_spec).split("-")[0]) or "1.0.0"
                    key = f"npm:{name.lower()}:{clean_ver}"
                    line_no, snippet = find_line_info(name)
                    scope, reason, conf = DependencyParser.determine_scope_details(rel_path, is_dev=True)
                    if key in components:
                        components[key].direct = True
                        if components[key].scope != "production":
                            components[key].scope = scope
                            components[key].scope_reason = reason
                            components[key].scope_confidence = conf
                    else:
                        components[key] = Component(
                            name=name.lower(),
                            version=clean_ver,
                            ecosystem="npm",
                            purl=f"pkg:npm/{name.lower()}@{clean_ver}",
                            direct=True,
                            manifest_path=rel_path,
                            scope=scope,
                            scope_reason=reason,
                            scope_confidence=conf,
                            line_number=line_no,
                            manifest_snippet=snippet
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
                    is_dev = bool(pkg_info.get("dev", False))
                    is_direct = pkg_key.count("node_modules/") == 1
                    
                    key = f"npm:{name.lower()}:{version}"
                    scope, reason, conf = DependencyParser.determine_scope_details(rel_path, is_dev=is_dev)
                    if key in components:
                        if is_direct:
                            components[key].direct = True
                    else:
                        components[key] = Component(
                            name=name.lower(),
                            version=version,
                            ecosystem="npm",
                            purl=f"pkg:npm/{name.lower()}@{version}",
                            direct=is_direct,
                            manifest_path=rel_path,
                            license=pkg_info.get("license", "Unknown"),
                            scope=scope,
                            scope_reason=reason,
                            scope_confidence=conf
                        )
            # npm lockfile v1 fallback
            elif "dependencies" in data and isinstance(data["dependencies"], dict):
                for name, dep_info in data["dependencies"].items():
                    ver = dep_info.get("version", "0.0.0")
                    is_dev = bool(dep_info.get("dev", False))
                    key = f"npm:{name.lower()}:{ver}"
                    scope, reason, conf = DependencyParser.determine_scope_details(rel_path, is_dev=is_dev)
                    if key not in components:
                        components[key] = Component(
                            name=name.lower(),
                            version=ver,
                            ecosystem="npm",
                            purl=f"pkg:npm/{name.lower()}@{ver}",
                            direct=True,
                            manifest_path=rel_path,
                            scope=scope,
                            scope_reason=reason,
                            scope_confidence=conf
                        )
        except Exception:
            pass

    @staticmethod
    def _parse_go_mod(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            in_require = False
            scope, reason, conf = DependencyParser.determine_scope_details(rel_path)
            for line_idx, raw_line in enumerate(content.splitlines(), 1):
                line = raw_line.strip()
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
                        manifest_path=rel_path,
                        scope=scope,
                        scope_reason=reason,
                        scope_confidence=conf,
                        line_number=line_idx,
                        manifest_snippet=line
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
                        manifest_path=rel_path,
                        scope=scope,
                        scope_reason=reason,
                        scope_confidence=conf,
                        line_number=line_idx,
                        manifest_snippet=line
                    )
        except Exception:
            pass

    @staticmethod
    def _parse_pom_xml(file_path: Path, repo_root: Path, components: Dict[str, Component]):
        rel_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            # Handle XML namespaces
            ns = {"m": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
            prefix = "m:" if ns else ""
            lines = content.splitlines()
            
            for dep in root.findall(f".//{prefix}dependency", ns):
                g = dep.find(f"{prefix}groupId", ns)
                a = dep.find(f"{prefix}artifactId", ns)
                v = dep.find(f"{prefix}version", ns)
                s = dep.find(f"{prefix}scope", ns)
                if g is not None and a is not None:
                    group_id = g.text.strip() if g.text else ""
                    art_id = a.text.strip() if a.text else ""
                    ver = v.text.strip() if v is not None and v.text else "unknown"
                    scope_val = s.text.strip().lower() if s is not None and s.text else "compile"
                    full_name = f"{group_id}:{art_id}"
                    key = f"maven:{full_name}:{ver}"

                    is_test = scope_val == "test"
                    is_dev = scope_val in ("provided", "system")
                    scope, reason, conf = DependencyParser.determine_scope_details(
                        rel_path, is_dev=is_dev, is_test=is_test, group=scope_val
                    )

                    line_no = None
                    snippet = None
                    for idx, l in enumerate(lines, 1):
                        if art_id in l:
                            line_no = idx
                            snippet = l.strip()
                            break

                    components[key] = Component(
                        name=full_name,
                        version=ver,
                        ecosystem="maven",
                        purl=f"pkg:maven/{group_id}/{art_id}@{ver}",
                        direct=True,
                        manifest_path=rel_path,
                        scope=scope,
                        scope_reason=reason,
                        scope_confidence=conf,
                        line_number=line_no,
                        manifest_snippet=snippet
                    )
        except Exception:
            pass

