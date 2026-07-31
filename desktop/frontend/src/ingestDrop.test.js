import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildDropResultMessage,
  classifyDroppedPaths,
  getPathExtension,
  isLikelySupportedIngestPath,
  normalizeDroppedPaths,
} from './ingestDrop.js';

test('normalizeDroppedPaths trims and deduplicates', () => {
  assert.deepEqual(
    normalizeDroppedPaths([' /tmp/a.md ', '/tmp/a.md', '', '   ', '/tmp/b.pdf']),
    ['/tmp/a.md', '/tmp/b.pdf'],
  );
});

test('getPathExtension returns lower-cased suffix', () => {
  assert.equal(getPathExtension('/tmp/Report.PDF'), '.pdf');
  assert.equal(getPathExtension('/tmp/Dockerfile'), '');
});

test('isLikelySupportedIngestPath accepts known files and extensionless directories', () => {
  assert.equal(isLikelySupportedIngestPath('/tmp/notes.md'), true);
  assert.equal(isLikelySupportedIngestPath('/tmp/paper.pdf'), true);
  assert.equal(isLikelySupportedIngestPath('/tmp/docs'), true);
  assert.equal(isLikelySupportedIngestPath('/tmp/Dockerfile'), true);
  assert.equal(isLikelySupportedIngestPath('/tmp/archive.zip'), false);
});

test('classifyDroppedPaths keeps supported items and skips unsupported ones', () => {
  assert.deepEqual(
    classifyDroppedPaths([
      '/tmp/docs',
      '/tmp/notes.md',
      '/tmp/archive.zip',
      '/tmp/script.py',
      '/tmp/photo.png',
    ]),
    {
      accepted: ['/tmp/docs', '/tmp/notes.md', '/tmp/script.py'],
      skipped: ['/tmp/archive.zip', '/tmp/photo.png'],
      skippedCount: 2,
      totalCount: 5,
    },
  );
});

test('buildDropResultMessage includes skipped count when present', () => {
  assert.equal(
    buildDropResultMessage({
      acceptedCount: 2,
      skippedCount: 1,
      project: 'lab',
      originLabel: 'chat',
    }),
    'Imported 2 path(s) into project lab from chat | skipped 1 unsupported item(s)',
  );
});
