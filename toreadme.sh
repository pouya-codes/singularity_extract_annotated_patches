
echo """# Extract Annotated Patches

## Usage

\`\`\`""" > README.md

python app.py -h >> README.md
echo >> README.md
python app.py from-experiment-manifest -h >> README.md
echo >> README.md
python app.py from-arguments -h >> README.md
echo >> README.md
echo "use-manifest is not implemented yet" >> README.md
echo >> README.md
python app.py from-arguments use-directory -h >> README.md
echo >> README.md
python app.py from-arguments use-directory use-slide-coords -h >> README.md
echo >> README.md
python app.py from-arguments use-directory use-annotation -h >> README.md
echo """\`\`\`
""" >> README.md

