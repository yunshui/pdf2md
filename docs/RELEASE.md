# Release Instructions

This document provides step-by-step instructions for releasing pdf2md version 0.1.0.

## Pre-Release Checklist

- [x] All tests passing (54/54 base tests)
- [x] Documentation complete
- [x] CHANGELOG.md updated
- [x] LICENSE file added
- [x] Version number updated in all files
- [x] Type annotations reviewed
- [ ] Full test coverage with dependencies installed
- [ ] Package build successful
- [ ] Installation from source successful

## Release Steps

### 1. Verify Version Information

```bash
# Check version in __init__.py
grep "__version__" pdf2md/__init__.py

# Should output: __version__ = "0.1.0"
```

### 2. Run Full Tests (with Dependencies)

```bash
# Install all dependencies
pip install pdfplumber pdf2image paddleocr Pillow click pytest-cov

# Run tests with coverage
python -m pytest tests/ -v --cov=pdf2md --cov-report=html

# Ensure all tests pass
```

### 3. Build the Package

```bash
# Build source distribution and wheel
python -m build

# Verify the built packages
ls -lh dist/
```

### 4. Test Installation

```bash
# Create a test virtual environment
python -m venv test_env
source test_env/bin/activate  # Linux/macOS
# or test_env\Scripts\activate  # Windows

# Install from built package
pip install dist/pdf2md-0.1.0-py3-none-any.whl

# Verify installation
python -c "from pdf2md import __version__; print(__version__)"

# Test basic functionality
python -c "from pdf2md.core import Pipeline; print('Import successful')"

# Deactivate
deactivate
```

### 5. Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Release version 0.1.0"

# Push tag to remote
git push origin v0.1.0
```

### 6. Create GitHub Release

1. Go to GitHub repository releases page
2. Click "Draft a new release"
3. Choose tag: `v0.1.0`
4. Release title: `v0.1.0 - Initial Release`
5. Release description: (copy from CHANGELOG.md)
6. Attach built packages (optional):
   - `dist/pdf2md-0.1.0.tar.gz`
   - `dist/pdf2md-0.1.0-py3-none-any.whl`
7. Click "Publish release"

### 7. Publish to PyPI (Optional)

**First-time setup:**
```bash
# Install twine
pip install twine

# Create PyPI account at https://pypi.org/account/register/

# Configure API token
# ~/.pypirc should contain:
# [pypi]
# username = __token__
# password = <your-api-token>
```

**Publish:**
```bash
# Upload to PyPI (test first)
twine upload --repository testpypi dist/*

# If successful, upload to PyPI
twine upload dist/*
```

### 8. Update Documentation

After release, update documentation to reference the released version:

- Update README.md with installation instructions
- Update any version-specific examples
- Announce release in community channels

### 9. Post-Release

- Monitor for issues and feedback
- Plan next release features
- Update CHANGELOG.md for next version

## Verification Steps

After release, verify:

```bash
# Install from PyPI (if published)
pip install pdf2md==0.1.0

# Test basic usage
pdf2md --help

# Test conversion (with sample PDF)
pdf2md -input sample.pdf
```

## Rollback Procedure

If issues are found after release:

```bash
# Delete PyPI version (if possible - contact PyPI support)
# Create yanked version
twine upload dist/* --skip-existing

# Or contact PyPI to remove the version
```

## Notes

- Always test thoroughly before releasing
- Keep CHANGELOG.md up to date
- Follow semantic versioning
- Tag releases in git for reference

## Current Status

- Version: 0.1.0
- Release Date: 2026-04-20
- Status: Ready for GitHub Release
- PyPI Status: Pending (optional step)