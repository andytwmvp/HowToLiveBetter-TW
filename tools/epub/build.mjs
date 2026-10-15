// 預設只匯出臺灣已核對導航；--source-preview 才匯出原作來源稿。
import { spawnSync } from 'node:child_process';
import { ROOT } from '../lib/book.mjs';
const args=process.argv.slice(2);
const output=args.find(x=>!x.startsWith('--'));
if(args.includes('--source-preview')) {
  process.argv.splice(2,process.argv.length,output || 'dist/HowToLiveBetter-source-preview.epub');
  await import('./source-preview.mjs');
} else {
  const result=spawnSync(process.env.PYTHON || 'python3',['tools/tw/edition.py','--format','epub','--output',output || 'dist/HowToLiveBetter-TW.epub'],{cwd:ROOT,stdio:'inherit'});
  if(result.error) throw result.error;
  process.exitCode=result.status ?? 1;
}
