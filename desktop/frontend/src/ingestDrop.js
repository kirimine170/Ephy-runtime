const SUPPORTED_INGEST_EXTENSIONS = new Set([
  '.md',
  '.markdown',
  '.txt',
  '.pdf',
  '.docx',
  '.html',
  '.htm',
  '.csv',
  '.tsv',
  '.json',
  '.py',
  '.js',
  '.ts',
  '.tsx',
  '.jsx',
  '.go',
  '.rs',
  '.java',
  '.c',
  '.cc',
  '.cpp',
  '.cxx',
  '.h',
  '.hpp',
  '.cs',
  '.rb',
  '.php',
  '.swift',
  '.kt',
  '.kts',
  '.scala',
  '.sql',
  '.sh',
  '.bash',
  '.zsh',
  '.yaml',
  '.yml',
  '.toml',
  '.ini',
  '.cfg',
  '.env',
]);

const SUPPORTED_INGEST_FILENAMES = new Set(['dockerfile']);

function normalizeDroppedPaths(paths) {
  if (!Array.isArray(paths)) {
    return [];
  }
  const seen = new Set();
  const normalized = [];
  paths.forEach((value) => {
    const path = String(value || '').trim();
    if (!path || seen.has(path)) {
      return;
    }
    seen.add(path);
    normalized.push(path);
  });
  return normalized;
}

function getPathLeafName(path) {
  return String(path).split(/[\\/]/).pop() || '';
}

function getPathExtension(path) {
  const leaf = getPathLeafName(path);
  const dotIndex = leaf.lastIndexOf('.');
  if (dotIndex <= 0) {
    return '';
  }
  return leaf.slice(dotIndex).toLowerCase();
}

function isLikelySupportedIngestPath(path) {
  const trimmed = String(path || '').trim();
  if (!trimmed) {
    return false;
  }

  const leaf = getPathLeafName(trimmed);
  const normalizedLeaf = leaf.toLowerCase();
  if (SUPPORTED_INGEST_FILENAMES.has(normalizedLeaf)) {
    return true;
  }

  const extension = getPathExtension(trimmed);
  if (SUPPORTED_INGEST_EXTENSIONS.has(extension)) {
    return true;
  }

  // Wails drag-and-drop only provides host paths, so the frontend cannot stat
  // them. Treat extensionless paths as likely directories and let backend ingest
  // decide whether they are supported.
  if (!leaf.includes('.')) {
    return true;
  }

  return false;
}

function classifyDroppedPaths(paths) {
  const normalized = normalizeDroppedPaths(paths);
  const accepted = [];
  const skipped = [];

  normalized.forEach((path) => {
    if (isLikelySupportedIngestPath(path)) {
      accepted.push(path);
      return;
    }
    skipped.push(path);
  });

  return {
    accepted,
    skipped,
    skippedCount: skipped.length,
    totalCount: normalized.length,
  };
}

function buildDropResultMessage({acceptedCount, skippedCount, project, originLabel}) {
  const parts = [`Imported ${acceptedCount} path(s)`];
  if (project) {
    parts.push(`into project ${project}`);
  } else {
    parts.push('into project (default)');
  }
  if (originLabel) {
    parts.push(`from ${originLabel}`);
  }
  if (skippedCount > 0) {
    parts.push(`| skipped ${skippedCount} unsupported item(s)`);
  }
  return parts.join(' ');
}

export {
  SUPPORTED_INGEST_EXTENSIONS,
  SUPPORTED_INGEST_FILENAMES,
  buildDropResultMessage,
  classifyDroppedPaths,
  getPathExtension,
  isLikelySupportedIngestPath,
  normalizeDroppedPaths,
};
