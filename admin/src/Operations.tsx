import { FormEvent, useState } from "react";
import { adminApi } from "./api";
import type { BillingPlan, Broker, Customer } from "./types";

interface Props {
  customers: Customer[];
  brokers: Broker[];
  plans: BillingPlan[];
  onChanged: () => Promise<void>;
}

export default function Operations({customers,brokers,plans,onChanged}:Props){
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState<string|null>(null);
  const [error,setError]=useState<string|null>(null);

  async function run(task:()=>Promise<unknown>, success:string){
    setBusy(true); setMessage(null); setError(null);
    try{await task(); setMessage(success); await onChanged()}
    catch(e){setError(e instanceof Error?e.message:String(e))}
    finally{setBusy(false)}
  }

  async function createBroker(e:FormEvent<HTMLFormElement>){
    e.preventDefault(); const f=new FormData(e.currentTarget);
    await run(()=>adminApi.createBroker({
      slug:String(f.get("slug")||"").trim().toLowerCase(),
      display_name:String(f.get("display_name")||"").trim(),
      adapter_key:String(f.get("adapter_key")||"").trim(),
      api_base_url:String(f.get("api_base_url")||"").trim()||null
    }),"Broker created.");
    e.currentTarget.reset();
  }

  async function referral(form:HTMLFormElement, verified:boolean){
    const f=new FormData(form);
    const customerId=String(f.get("customer_id")||""); const broker=String(f.get("broker_slug")||"");
    await run(()=>adminApi.verifyReferral(customerId,verified,verified?broker:null),verified?"Referral verified.":"Referral verification removed.");
  }

  async function notify(e:FormEvent<HTMLFormElement>){
    e.preventDefault(); const f=new FormData(e.currentTarget);
    await run(()=>adminApi.queueNotification({customer_id:String(f.get("customer_id")||""),title:String(f.get("title")||""),body:String(f.get("body")||"")}),"Notification queued.");
    e.currentTarget.reset();
  }

  async function createPlan(e:FormEvent<HTMLFormElement>){
    e.preventDefault(); const f=new FormData(e.currentTarget);
    const rands=Number(f.get("price_zar")||0);
    await run(()=>adminApi.createBillingPlan({
      code:String(f.get("code")||"").trim().toLowerCase(),
      display_name:String(f.get("display_name")||"").trim(),
      product:String(f.get("product")||""),
      currency:"ZAR", price_minor:Math.round(rands*100),
      broker_discount_percent:Number(f.get("discount")||70)
    }),"Billing plan created.");
    e.currentTarget.reset();
  }

  return <div className="stack">
    {(message||error)&&<div className={error?"error-box inline":"success-box"}>{error||message}</div>}
    <div className="operations-grid">
      <section className="panel"><div className="panel-heading"><h2>Add broker</h2><span>{brokers.length} active</span></div>
        <form className="action-form" onSubmit={createBroker}>
          <label>Slug<input name="slug" placeholder="ic-markets" required/></label>
          <label>Display name<input name="display_name" placeholder="IC Markets" required/></label>
          <label>Adapter key<input name="adapter_key" placeholder="mt5_windows" required/></label>
          <label>API base URL<input name="api_base_url" placeholder="Optional"/></label>
          <button className="primary-button" disabled={busy}>Create broker</button>
        </form>
      </section>

      <section className="panel"><div className="panel-heading"><h2>Broker referral</h2><span>70% discount control</span></div>
        <form className="action-form" onSubmit={(e)=>{e.preventDefault(); void referral(e.currentTarget,true)}}>
          <label>Customer<select name="customer_id" required>{customers.map(c=><option key={c.id} value={c.id}>{c.full_name+" - "+c.email}</option>)}</select></label>
          <label>Broker<select name="broker_slug" required>{brokers.map(b=><option key={b.id} value={b.slug}>{b.display_name}</option>)}</select></label>
          <div className="form-actions"><button className="primary-button" disabled={busy||!customers.length||!brokers.length}>Verify</button>
          <button type="button" className="secondary-button" disabled={busy||!customers.length} onClick={(e)=>{if(e.currentTarget.form) void referral(e.currentTarget.form,false)}}>Remove</button></div>
        </form>
      </section>

      <section className="panel"><div className="panel-heading"><h2>Push / inbox notification</h2><span>Customer messaging</span></div>
        <form className="action-form" onSubmit={notify}>
          <label>Customer<select name="customer_id" required>{customers.map(c=><option key={c.id} value={c.id}>{c.full_name+" - "+c.email}</option>)}</select></label>
          <label>Title<input name="title" maxLength={180} required/></label>
          <label>Message<textarea name="body" rows={4} maxLength={4000} required/></label>
          <button className="primary-button" disabled={busy||!customers.length}>Queue notification</button>
        </form>
      </section>

      <section className="panel"><div className="panel-heading"><h2>Add billing plan</h2><span>{plans.length} active</span></div>
        <form className="action-form" onSubmit={createPlan}>
          <label>Code<input name="code" placeholder="scalper-monthly" required/></label>
          <label>Name<input name="display_name" placeholder="Abutron Scalper Monthly" required/></label>
          <label>Product<select name="product"><option value="flipper">Flipper</option><option value="scalper">Scalper</option><option value="master">Master</option></select></label>
          <label>Price ZAR<input name="price_zar" type="number" min="1" step="0.01" required/></label>
          <label>Broker discount %<input name="discount" type="number" min="0" max="100" defaultValue="70" required/></label>
          <button className="primary-button" disabled={busy}>Create plan</button>
        </form>
      </section>
    </div>
  </div>
}
