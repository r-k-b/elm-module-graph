#!/usr/bin/env python

import argparse
import json
import io
import os
import re
import sys
from functools import reduce


re_import = re.compile(r"{-.*?-}|^import\s+([A-Z][\w\.]*)", re.DOTALL | re.MULTILINE)

# source text -> [modulename]
def extract_imports(text):
    return filter(lambda s: s != "" and s[0:7] != "Native.", re_import.findall(text))


# source text -> modulename
def extract_modulename(text):
    match = re.match(r"(?:port )?module\s+([A-Z][\w\.]*)", text)
    return match.group(1) if match is not None else None


# repo path -> "<user>/<project>"
def extract_packagename(repository):
    match = re.search(r"([^\/]+\/[^\/]+?)(\.\w+)?$", repository)
    return match.group(1) if match is not None else None


# -> maybe filepath of nearest elm.json
def find_elmjson(path):
    elmjson = os.path.join(path, "elm.json")
    if not os.path.exists(path) or os.path.ismount(path):
        return None
    elif os.path.isfile(elmjson):
        return elmjson
    else:
        return find_elmjson(os.path.dirname(path))


# -> {"sourcedirs": [dir], "dependencies": [packagename]}
def get_packageinfo(packagedir):
    elmjson = json.load(open(os.path.join(packagedir, "elm.json")))
    if elmjson.get("type") == "application":
        dependencies = list(elmjson.get("dependencies", {}).get("direct", {}).keys())
        indirect_dependencies = list(elmjson.get("dependencies", {}).get("indirect", {}).keys())
    else:
        dependencies = list(elmjson.get("dependencies", {}).keys())
        indirect_dependencies = []
    print 
    return {
        "sourcedirs": list(map(
            lambda dir: os.path.normpath(os.path.join(packagedir, dir)),
            elmjson.get("source-directories", ["src"])
        )),
        "dependencies": dependencies + indirect_dependencies,
        "indirect_dependencies": indirect_dependencies
    }


# -> (packagename, modulename, sourcepath)
def find_importedmodule(packages, packagename, importedmodulename):
    sourcedirs = list(map(tuple(packagename), packages[packagename]["sourcedirs"]))
    dependencysourcedirs = list(concatmap(lambda dep: list(map(tuple(dep), packages[dep]["sourcedirs"])), packages[packagename]["dependencies"]))
    segments = importedmodulename.split(".")
    for (importedpackagename, sourcedir) in (list(sourcedirs) + list(dependencysourcedirs)):
        sourcepath = os.path.join(sourcedir, *segments) + ".elm"
        if os.path.isfile(sourcepath):
            return (importedpackagename, importedmodulename, sourcepath)

    print("warning: source file not found for module (" + importedmodulename +") as imported from (" + packagename + ")")
    return None


def tuple(a):
    return lambda b: (a, b)


def concatmap(f, l):
    return reduce(lambda r, x: r + f(x), l, [])


# -> {qualifiedmodulename: {"imports": [qualifiedmodulename], "package": packagename}}
def graph_from_imports(packages, packagename, modulename, importedmodulenames, graph):
    importedmodules = list(filter(
        lambda x: x is not None,
        map(lambda m: find_importedmodule(packages, packagename, m), importedmodulenames)
    ))
    graph[qualify(packagename, modulename)] = {
        "imports": list(map(lambda t: qualify(t[0], t[1]), importedmodules)),
        "package": packagename
    }
    return reduce(
        lambda g, t: graph_from_imports(packages, t[0], t[1], extract_imports(open(t[2]).read()), g),
        filter(
            lambda t: qualify(t[0], t[1]) not in graph,
            importedmodules
        ),
        graph
    )


def qualify(packagename, modulename):
    return packagename + " " + modulename


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="module-graph.json", help="file to write to (default: module-graph.json)")
    parser.add_argument("filepath", help="path to .elm file or elm.json")
    args = parser.parse_args()

    filepath = os.path.abspath(args.filepath)

    if not os.path.isfile(filepath):
        print("error: file not found: " + filepath)
        sys.exit(1)

    elmjson = filepath if os.path.basename(filepath) == "elm.json" else find_elmjson(filepath)

    if elmjson is None:
        print("error: elm.json not found for: " + filepath)
        sys.exit(1)

    projectdir = os.path.dirname(elmjson)

    if not os.path.exists(os.path.join(projectdir, "elm-stuff")):
        print("error: elm-stuff folder not found (run elm-make and try again)")
        sys.exit(1)

    # packages (dict), projectname, entryname, modulenames (list)
    elmjsondata = json.load(open(elmjson))
    projectname = extract_packagename(elmjsondata.get("repository", "")) or "user/project"

    packages = {projectname: get_packageinfo(projectdir)} 

    if elmjsondata.get('type') == 'application':
        deps = elmjsondata.get('dependencies', {}).get('direct', {}) | elmjsondata.get('dependencies', {}).get('indirect', {})
    else:
        print("error: can not get exact dependencies for a package; please try an application")
        sys.exit(1)

    elmhome = os.path.expanduser(os.environ.get('ELM_HOME', os.path.expanduser("~/.elm")))
    elmversion = "0.19.1"
    for packagename, version in deps.items():
        packages[packagename] = get_packageinfo(os.path.join(elmhome, elmversion, "packages", packagename, version))

    if filepath == elmjson:
        entryname = "exposed-modules"
        modulenames = elmjsondata.get("exposed-modules", [])
    else:
        sourcetext = open(filepath).read()
        entryname = extract_modulename(sourcetext) or "Main"
        modulenames = extract_imports(sourcetext)

    # graph
    modulegraph = graph_from_imports(packages, projectname, entryname, modulenames, {})

    output = io.open(args.output, "wt", encoding="utf-8")
    output.write(json.dumps(modulegraph, indent=2, separators=[",", ": "]))
    output.close()


if __name__ == "__main__":
    main()
