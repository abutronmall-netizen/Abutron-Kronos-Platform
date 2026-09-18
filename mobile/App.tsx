import React,{useEffect,useMemo,useState} from "react";
import {ActivityIndicator,Alert,Platform,Pressable,RefreshControl,SafeAreaView,ScrollView,StatusBar,StyleSheet,Text,TextInput,View} from "react-native";
import * as Crypto from "expo-crypto";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";
import {Bootstrap,Notice,bootstrap as loadBootstrap,device,login,notices,readNotice,register} from "./src/api";

const TOKEN="abutron_access_token", DEVICE="abutron_device_id";
type Screen="home"|"accounts"|"alerts"|"profile";
function Button({title,onPress,secondary=false}:{title:string;onPress:()=>void;secondary?:boolean}){return <Pressable onPress={onPress} style={[s.button,secondary&&s.secondary]}><Text style={s.buttonText}>{title}</Text></Pressable>}
function Card({children}:{children:React.ReactNode}){return <View style={s.card}>{children}</View>}
async function deviceId(){let id=await SecureStore.getItemAsync(DEVICE);if(id)return id;id=Crypto.randomUUID();await SecureStore.setItemAsync(DEVICE,id);return id}
async function pushToken(){
 if(!Device.isDevice)return null; let p=await Notifications.getPermissionsAsync();
 if(p.status!=="granted")p=await Notifications.requestPermissionsAsync(); if(p.status!=="granted")return null;
 const projectId=Constants.expoConfig?.extra?.eas?.projectId||Constants.easConfig?.projectId;
 if(!projectId||projectId==="REPLACE_WITH_EAS_PROJECT_ID")return null;
 return (await Notifications.getExpoPushTokenAsync({projectId})).data;
}
export default function App(){
 const[token,setToken]=useState<string|null>(null),[data,setData]=useState<Bootstrap|null>(null),[alerts,setAlerts]=useState<Notice[]>([]);
 const[screen,setScreen]=useState<Screen>("home"),[busy,setBusy]=useState(true),[refreshing,setRefreshing]=useState(false),[mode,setMode]=useState<"login"|"register">("login");
 const[email,setEmail]=useState(""),[password,setPassword]=useState(""),[name,setName]=useState(""),[phone,setPhone]=useState("");
 const unread=useMemo(()=>alerts.filter(x=>!x.read_at).length,[alerts]);
 useEffect(()=>{SecureStore.getItemAsync(TOKEN).then(async t=>{setToken(t);if(t)await refresh(t)}).catch(e=>Alert.alert("Startup error",String(e))).finally(()=>setBusy(false))},[]);
 async function refresh(active=token){if(!active)return;setRefreshing(true);try{
  const [b,n]=await Promise.all([loadBootstrap(active),notices(active)]);setData(b);setAlerts(n);
  await device(active,{platform:Platform.OS==="ios"?"ios":"android",device_id:await deviceId(),push_token:await pushToken(),app_version:Constants.expoConfig?.version||"2.44.0"});
 }catch(e){Alert.alert("Refresh failed",e instanceof Error?e.message:String(e))}finally{setRefreshing(false)}}
 async function auth(){setBusy(true);try{if(mode==="register")await register(name.trim(),email.trim(),password,phone.trim());
  const r=await login(email.trim(),password);await SecureStore.setItemAsync(TOKEN,r.access_token);setToken(r.access_token);await refresh(r.access_token);
 }catch(e){Alert.alert("Authentication failed",e instanceof Error?e.message:String(e))}finally{setBusy(false)}}
 async function logout(){await SecureStore.deleteItemAsync(TOKEN);setToken(null);setData(null);setAlerts([]);setScreen("home")}
 async function openNotice(n:Notice){if(token&&!n.read_at){try{const u=await readNotice(token,n.id);setAlerts(a=>a.map(x=>x.id===u.id?u:x))}catch{}}Alert.alert(n.title,n.body)}
 if(busy)return <SafeAreaView style={s.center}><StatusBar barStyle="light-content"/><ActivityIndicator size="large"/><Text style={s.muted}>Starting Abutron...</Text></SafeAreaView>;
 if(!token)return <SafeAreaView style={s.root}><StatusBar barStyle="light-content"/><ScrollView contentContainerStyle={s.auth}>
  <Text style={s.brand}>ABUTRON</Text><Text style={s.title}>{mode==="login"?"Welcome back":"Create account"}</Text><Text style={s.muted}>Trading platform control, licensing and account status.</Text>
  {mode==="register"&&<><TextInput style={s.input} placeholder="Full name" placeholderTextColor="#697386" value={name} onChangeText={setName}/><TextInput style={s.input} placeholder="Phone" placeholderTextColor="#697386" value={phone} onChangeText={setPhone}/></>}
  <TextInput style={s.input} autoCapitalize="none" keyboardType="email-address" placeholder="Email" placeholderTextColor="#697386" value={email} onChangeText={setEmail}/>
  <TextInput style={s.input} secureTextEntry placeholder="Password" placeholderTextColor="#697386" value={password} onChangeText={setPassword}/>
  <Button title={mode==="login"?"Sign in":"Register"} onPress={auth}/><Button secondary title={mode==="login"?"Create an account":"I already have an account"} onPress={()=>setMode(mode==="login"?"register":"login")}/>
 </ScrollView></SafeAreaView>;
 const accounts=data?.accounts||[],licenses=data?.licenses||[],customer=data?.customer;
 return <SafeAreaView style={s.root}><StatusBar barStyle="light-content"/><View style={s.header}><View><Text style={s.brandSmall}>ABUTRON</Text><Text style={s.headerTitle}>{screen.toUpperCase()}</Text></View><Pressable onPress={()=>refresh()}><Text style={s.link}>Refresh</Text></Pressable></View>
 <ScrollView style={{flex:1}} contentContainerStyle={s.content} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={()=>refresh()} tintColor="#fff"/>}>
 {screen==="home"&&<><Text style={s.title}>{"Hello "+(customer?.full_name||"")}</Text><Card><Text style={s.metric}>{accounts.length}</Text><Text style={s.muted}>Trading accounts</Text></Card><Card><Text style={s.metric}>{licenses.filter(x=>x.status==="active").length}</Text><Text style={s.muted}>Active licenses</Text></Card><Card><Text style={s.metric}>{unread}</Text><Text style={s.muted}>Unread alerts</Text></Card>
  {accounts[0]&&<Card><Text style={s.cardTitle}>Primary account</Text><Text style={s.row}>{"Login: "+accounts[0].broker_login}</Text><Text style={s.row}>{"Equity: $"+String(accounts[0].equity_usd)}</Text><Text style={s.row}>{"Bot: "+accounts[0].bot_tier}</Text><Text style={s.row}>{"Status: "+accounts[0].status}</Text></Card>}</>}
 {screen==="accounts"&&<>{accounts.length===0&&<Text style={s.muted}>No trading accounts registered.</Text>}{accounts.map(a=><Card key={a.id}><Text style={s.cardTitle}>{a.broker_login}</Text><Text style={s.row}>{"Server: "+(a.server_name||"-")}</Text><Text style={s.row}>{"Equity: $"+String(a.equity_usd)}</Text><Text style={s.row}>{"Assigned bot: "+a.bot_tier}</Text><Text style={s.row}>{"Route: "+a.route_reason}</Text><Text style={s.row}>{"Status: "+a.status}</Text></Card>)}{licenses.map(l=><Card key={l.id}><Text style={s.cardTitle}>{l.product+" license"}</Text><Text style={s.row}>{"Status: "+l.status}</Text></Card>)}</>}
 {screen==="alerts"&&<>{alerts.length===0&&<Text style={s.muted}>No notifications.</Text>}{alerts.map(n=><Pressable key={n.id} onPress={()=>openNotice(n)}><Card><Text style={s.cardTitle}>{n.title+(!n.read_at?" - NEW":"")}</Text><Text style={s.row} numberOfLines={2}>{n.body}</Text><Text style={s.meta}>{new Date(n.created_at).toLocaleString()}</Text></Card></Pressable>)}</>}
 {screen==="profile"&&<><Card><Text style={s.cardTitle}>{customer?.full_name}</Text><Text style={s.row}>{customer?.email}</Text><Text style={s.row}>{customer?.phone||""}</Text><Text style={s.row}>{"Referral verified: "+(customer?.broker_referral_verified?"Yes":"No")}</Text></Card><Button secondary title="Sign out" onPress={logout}/></>}
 </ScrollView><View style={s.nav}>{(["home","accounts","alerts","profile"] as Screen[]).map(x=><Pressable key={x} style={s.navItem} onPress={()=>setScreen(x)}><Text style={[s.navText,screen===x&&s.navActive]}>{x==="alerts"&&unread?"Alerts ("+unread+")":x}</Text></Pressable>)}</View></SafeAreaView>
}
const s=StyleSheet.create({root:{flex:1,backgroundColor:"#070B14"},center:{flex:1,backgroundColor:"#070B14",alignItems:"center",justifyContent:"center",gap:12},auth:{flexGrow:1,justifyContent:"center",padding:24,gap:14},brand:{color:"#7AE7FF",fontSize:34,fontWeight:"900",letterSpacing:5},brandSmall:{color:"#7AE7FF",fontSize:13,fontWeight:"900",letterSpacing:3},title:{color:"#fff",fontSize:28,fontWeight:"800",marginBottom:4},muted:{color:"#96A0B5",fontSize:14,lineHeight:20},input:{backgroundColor:"#111827",borderColor:"#263248",borderWidth:1,color:"#fff",borderRadius:12,paddingHorizontal:14,paddingVertical:14},button:{backgroundColor:"#1667FF",borderRadius:12,paddingVertical:14,alignItems:"center",marginTop:4},secondary:{backgroundColor:"#182235"},buttonText:{color:"#fff",fontSize:15,fontWeight:"800"},header:{paddingHorizontal:18,paddingVertical:14,borderBottomColor:"#172033",borderBottomWidth:1,flexDirection:"row",alignItems:"center",justifyContent:"space-between"},headerTitle:{color:"#fff",fontWeight:"800",fontSize:17,marginTop:3},link:{color:"#7AE7FF",fontWeight:"700"},content:{padding:16,gap:12,paddingBottom:28},card:{backgroundColor:"#101827",borderColor:"#23304A",borderWidth:1,borderRadius:16,padding:16,marginBottom:10},cardTitle:{color:"#fff",fontWeight:"800",fontSize:16,marginBottom:8},row:{color:"#D8DEEA",fontSize:14,marginBottom:5},meta:{color:"#697386",fontSize:12,marginTop:8},metric:{color:"#fff",fontSize:34,fontWeight:"900"},nav:{flexDirection:"row",borderTopColor:"#172033",borderTopWidth:1,backgroundColor:"#0A101C",paddingVertical:10},navItem:{flex:1,alignItems:"center",paddingVertical:8},navText:{color:"#768198",fontSize:11,textTransform:"capitalize"},navActive:{color:"#7AE7FF",fontWeight:"800"}});
