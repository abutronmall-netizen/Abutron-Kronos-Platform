export type Account = { id:string; broker_login:string; server_name?:string|null; equity_usd:string|number; bot_tier:string; route_reason:string; status:string };
export type License = { id:string; product:string; status:string; starts_at?:string|null; expires_at?:string|null };
export type Bootstrap = { customer:{full_name:string;email:string;phone?:string|null;broker_referral_verified:boolean}; accounts:Account[]; licenses:License[]; feature_flags:Record<string,boolean> };
export type Notice = { id:string; title:string; body:string; created_at:string; read_at?:string|null };
const BASE=(process.env.EXPO_PUBLIC_ABUTRON_API_URL||"").replace(/\/+$/,"");
async function req<T>(path:string, init:RequestInit={}, token?:string|null):Promise<T>{
  if(!BASE) throw new Error("EXPO_PUBLIC_ABUTRON_API_URL is not configured");
  const headers:Record<string,string>={"Content-Type":"application/json",...(init.headers as Record<string,string>|undefined)};
  if(token) headers.Authorization="Bearer "+token;
  const r=await fetch(BASE+path,{...init,headers}); const raw=await r.text(); let body:any=null;
  if(raw){try{body=JSON.parse(raw)}catch{body=raw}}
  if(!r.ok) throw new Error(body?.detail||("Request failed: "+r.status)); return body as T;
}
export const login=(email:string,password:string)=>req<{access_token:string;expires_in:number}>("/api/v1/auth/login",{method:"POST",body:JSON.stringify({email,password})});
export const register=(full_name:string,email:string,password:string,phone:string)=>req("/api/v1/auth/register",{method:"POST",body:JSON.stringify({full_name,email,password,phone:phone||null})});
export const bootstrap=(token:string)=>req<Bootstrap>("/api/v1/mobile/bootstrap",{},token);
export const notices=(token:string)=>req<Notice[]>("/api/v1/notifications",{},token);
export const readNotice=(token:string,id:string)=>req<Notice>("/api/v1/notifications/"+encodeURIComponent(id)+"/read",{method:"PATCH"},token);
export const device=(token:string,payload:object)=>req("/api/v1/devices",{method:"PUT",body:JSON.stringify(payload)},token);
