const ts = require('C:/PATCHPROOF/frontend/node_modules/typescript');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

function normalizeJsCode(code) {
    try {
        const sourceFile = ts.createSourceFile('snippet.ts', code, ts.ScriptTarget.Latest, true);
        
        let modified = false;
        function visit(node) {
            if (ts.isFunctionDeclaration(node) || ts.isArrowFunction(node) || ts.isFunctionExpression(node) || ts.isMethodDeclaration(node)) {
                const localMap = new Map();
                let pIdx = 1;
                for (const param of node.parameters) {
                    if (ts.isIdentifier(param.name)) {
                        localMap.set(param.name.text, `p_${pIdx++}`);
                    }
                }
                
                let vIdx = 1;
                function collectLocals(n) {
                    if (n !== node && (ts.isFunctionDeclaration(n) || ts.isArrowFunction(n) || ts.isFunctionExpression(n))) {
                        return;
                    }
                    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name)) {
                        const name = n.name.text;
                        if (!localMap.has(name)) {
                            localMap.set(name, `v_${vIdx++}`);
                        }
                    }
                    ts.forEachChild(n, collectLocals);
                }
                if (node.body) {
                    collectLocals(node.body);
                }
                
                if (localMap.size === 0) return code;
                
                const transformer = (context) => (rootNode) => {
                    function transform(n) {
                        if (ts.isIdentifier(n)) {
                            const parent = n.parent;
                            if (parent && ts.isPropertyAccessExpression(parent) && parent.name === n) return n;
                            if (parent && ts.isPropertyAssignment(parent) && parent.name === n) return n;
                            if (parent && ts.isFunctionDeclaration(parent) && parent.name === n) return n;
                            if (localMap.has(n.text)) {
                                modified = true;
                                return context.factory.createIdentifier(localMap.get(n.text));
                            }
                        }
                        return ts.visitEachChild(n, transform, context);
                    }
                    return ts.visitNode(rootNode, transform);
                };
                
                const result = ts.transform(node, [transformer]);
                const printer = ts.createPrinter({ newLine: ts.NewLineKind.LineFeed });
                return printer.printNode(ts.EmitHint.Unspecified, result.transformed[0], sourceFile);
            }
            return ts.forEachChild(node, visit);
        }
        
        const res = visit(sourceFile);
        return res || code;
    } catch (e) {
        return code;
    }
}

rl.on('line', (line) => {
    if (!line.trim()) return;
    try {
        const item = JSON.parse(line);
        const norm = normalizeJsCode(item.code);
        console.log(JSON.stringify({ id: item.id, code: norm }));
    } catch(err) {
        console.log(JSON.stringify({ id: null, code: null, error: err.message }));
    }
});

