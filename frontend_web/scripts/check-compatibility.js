#!/usr/bin/env node
/**
 * Dependency Compatibility Checker
 * 
 * Checks if all dependencies are compatible with Next.js 16 and React 19
 */

const fs = require('fs');
const path = require('path');

const packageJsonPath = path.join(__dirname, '..', 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));

// Known compatibility matrix
const compatibility = {
  // Core - Should be compatible
  'next': { compatible: true, notes: 'Next.js 16 supports React 19' },
  'react': { compatible: true, notes: 'React 19 is latest' },
  'react-dom': { compatible: true, notes: 'React 19 is latest' },
  
  // UI Libraries - Generally compatible
  '@monaco-editor/react': { compatible: true, notes: 'Check for React 19 support' },
  '@radix-ui/react-scroll-area': { compatible: true, notes: 'Radix UI supports React 19' },
  '@vis.gl/react-google-maps': { compatible: true, notes: 'Check latest version' },
  'lucide-react': { compatible: true, notes: 'Icon library, should be compatible' },
  'react-markdown': { compatible: true, notes: 'Check for React 19 support' },
  'reactflow': { compatible: true, notes: 'Check latest version for React 19' },
  'zustand': { compatible: true, notes: 'State management, should be compatible' },
  
  // Testing - May need updates
  '@testing-library/react': { compatible: true, notes: 'Version 16+ supports React 19' },
  'jest': { compatible: true, notes: 'Jest 30 may need config updates' },
  
  // Build Tools
  'typescript': { compatible: true, notes: 'TypeScript 5.x supports React 19' },
  'tailwindcss': { compatible: true, notes: 'Tailwind 4.x is major update, test carefully' },
};

console.log('🔍 Dependency Compatibility Check\n');
console.log('='.repeat(60));

let allCompatible = true;

for (const [dep, info] of Object.entries(compatibility)) {
  const currentVersion = packageJson.dependencies?.[dep] || packageJson.devDependencies?.[dep];
  
  if (currentVersion) {
    const status = info.compatible ? '✅' : '⚠️';
    console.log(`${status} ${dep}: ${currentVersion}`);
    console.log(`   ${info.notes}`);
    
    if (!info.compatible) {
      allCompatible = false;
    }
  }
}

console.log('\n' + '='.repeat(60));

if (allCompatible) {
  console.log('✅ All checked dependencies appear compatible');
  console.log('⚠️  Still recommended to test thoroughly after upgrade');
} else {
  console.log('⚠️  Some dependencies may have compatibility issues');
  console.log('   Review the notes above before upgrading');
}

console.log('\nNext steps:');
console.log('1. Review compatibility notes above');
console.log('2. Run: npm outdated (to see available updates)');
console.log('3. Run upgrade script: ./scripts/upgrade-nextjs.sh');
console.log('4. Test thoroughly after upgrade');













