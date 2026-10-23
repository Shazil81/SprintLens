/** Generate explicit Vercel routing before deployment; this script never contacts the backend. */
import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath, pathToFileURL} from 'node:url';

export function productionConfig(origin) {
  let url;
  try {url = new URL(origin);} catch {throw new Error('Provide the public HTTPS backend origin.');}
  if(url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/' ||
      !url.hostname.includes('.') || /(^|\.)(localhost|invalid)$/.test(url.hostname) || url.hostname === '127.0.0.1') {
    throw new Error('Use an HTTPS backend origin without credentials, paths, query strings or placeholder hosts.');
  }
  const security = [
    {key:'X-Content-Type-Options',value:'nosniff'},
    {key:'X-Frame-Options',value:'DENY'},
    {key:'Referrer-Policy',value:'strict-origin-when-cross-origin'},
    {key:'Permissions-Policy',value:'camera=(), microphone=(), geolocation=()'},
    {key:'Content-Security-Policy',value:"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"},
  ];
  return {
    $schema:'https://openapi.vercel.sh/vercel.json',framework:'vite',
    buildCommand:'npm run build:vercel',outputDirectory:'dist',
    // Capture the entire path, including Django's required trailing slash.
    rewrites:[{source:'/api/:path(.*)',destination:`${url.origin}/api/:path`},{source:'/:path(.*)',destination:'/index.html'}],
    headers:[{source:'/:path(.*)',headers:security},{source:'/api/:path(.*)',headers:[
      {key:'Cache-Control',value:'private, no-store, max-age=0'},
      {key:'CDN-Cache-Control',value:'no-store'},
      {key:'Vercel-CDN-Cache-Control',value:'no-store'},
    ]}],
  };
}

export function checkConfig(config) {
  const destination = config?.rewrites?.[0]?.destination;
  if(typeof destination !== 'string' || !destination.endsWith('/api/:path')) throw new Error('Missing the production /api rewrite.');
  const expected = productionConfig(destination.slice(0,-'/api/:path'.length));
  if(JSON.stringify(config) !== JSON.stringify(expected)) throw new Error('Vercel routing differs from the reviewed template. Regenerate it with the real backend origin.');
}

if(process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const target = fileURLToPath(new URL('../vercel.json',import.meta.url));
  try {
    if(process.argv[2] === '--check') {
      checkConfig(JSON.parse(readFileSync(target,'utf8')));
      console.log('Production Vercel configuration verified.');
    } else {
      const config = productionConfig(process.argv[2]);
      writeFileSync(target,JSON.stringify(config,null,2)+'\n');
      console.log('Created frontend/vercel.json. Commit it before creating the Vercel deployment.');
    }
  } catch(error) {
    console.error(error.code === 'ENOENT' ? 'Configure production routing first: node scripts/configure-production.mjs https://YOUR-API.onrender.com' : error.message);
    process.exitCode = 1;
  }
}
