import io
from pathlib import Path
from scipy import sparse
import numpy as np
import pandas as pd
import streamlit as st

try:
    from scipy.optimize import milp, LinearConstraint, Bounds
    SCIPY_OK = True
except Exception:
    SCIPY_OK = False

APP_TITLE = "TMD 3 – AI-Assisted Transfer Planner"
MODEL_FILE = Path("TMD3_Model_Data.xlsx")
ZONES = {
    1: ["Agartala","Aizawl","Gangtok","Guwahati","Imphal","Itanagar","Kohima","Shillong"],
    2: ["Bhubaneswar","Kolkata","Patna","Raipur","Ranchi"],
    3: ["Bengaluru","Chennai","Hyderabad","Kochi","Thiruvananthapuram","Vijayawada"],
    4: ["Mumbai","Panaji","Pune"],
    5: ["Ahmedabad","Bhopal","Kanpur","Lucknow","Nagpur"],
    6: ["Chandigarh","Dehradun","Jaipur","Jammu and Srinagar","New Delhi","Shimla"],
}
CENTRE_ZONE = {c:z for z,cs in ZONES.items() for c in cs}
ALL_CENTRES = list(CENTRE_ZONE)
SPECIALIST = {"DEPR","DSIM","Legal","Rajbhasha"}
CADRES = ["CSG","DEPR","DSIM","Legal","Rajbhasha"]
GRADES = list("ABCDEF")
PREF_SAT = {1:100, 2:75, 3:50, 4:25, 5:50, 99:-25}
PREF_SCORE = {1:100, 2:75, 3:50, 4:25, 5:50}
PAR_PRIORITY_THRESHOLD = 9.0
PAR_WEIGHT = 15.0
PAR_YEAR_COLS = [f"PAR_{y}" for y in range(2022, 2027)]
MAX_NER_EXTENSION_YEARS = 1
VALID_OFFICER_IDS = {f"{i:04d}" for i in range(1,5001)}

st.set_page_config(page_title=APP_TITLE, page_icon="🏛️", layout="wide")
st.markdown("""
<style>
:root{--navy:#17365D;--blue:#1F4E78;--muted:#667085;--line:#D9E1EA;--green:#0F6B4A;--amber:#9A6700;--red:#B42318;--bg:#F7F9FC}
.stApp{background:#fff}.block-container{max-width:1550px;padding-top:1rem;padding-bottom:3rem}
.hero{border:1px solid var(--line);border-left:7px solid var(--navy);border-radius:12px;padding:18px 24px;background:linear-gradient(90deg,#F5F8FC,#fff);margin-bottom:16px}
.hero h1{color:var(--navy);margin:0;font-size:2rem}.hero p{color:var(--muted);margin:5px 0 0}
.section{color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:7px;margin-top:20px}
.answer{border-radius:12px;padding:18px 22px;margin-top:18px;border:2px solid #1B7F5B;background:#ECFDF3}
.answer h2{margin:0 0 6px;color:#075E42}.answer .big{font-size:1.45rem;font-weight:700;color:#064E3B}
.review{border-color:#C58A00;background:#FFF8E1}.review h2,.review .big{color:#7A5200}
.danger{border-color:#B42318;background:#FEF3F2}.danger h2,.danger .big{color:#912018}
.kpi{border:1px solid var(--line);border-radius:10px;padding:12px;background:#fff}
.small{font-size:.85rem;color:var(--muted)}
</style>
""", unsafe_allow_html=True)
st.markdown(f'<div class="hero"><h1>🏛️ {APP_TITLE}</h1><p>Policy-first • AI-assisted • Whole-batch optimisation • Workforce planning • Human-approved</p></div>', unsafe_allow_html=True)

@st.cache_data
def load_data():
    m = pd.read_excel(MODEL_FILE, sheet_name="Officer_Master")
    c = pd.read_excel(MODEL_FILE, sheet_name="Centre_Capacity")
    a = pd.read_excel(MODEL_FILE, sheet_name="Assumptions")
    s = pd.read_excel(MODEL_FILE, sheet_name="Specialist_Cadre_Rules")
    m["Officer_ID"] = m["Officer_ID"].astype(str).str.extract(r"(\d+)")[0].str.zfill(4)
    for col in ["Centre_Joining_Date","Date_of_Birth","Retirement_Date"]:
        if col in m.columns: m[col] = pd.to_datetime(m[col], errors="coerce")
    m["Recruitment_Mode"] = m.apply(lambda r: "Direct" if r["Grade"]=="B" and str(r["Recruitment_Mode"])=="Direct" else "Merit" if r["Grade"] in ["A","B"] else str(r["Recruitment_Mode"]), axis=1)
    # Annual PAR marks are whole-number ratings; the five-year average may be decimal.
    for col in PAR_YEAR_COLS:
        if col in m.columns:
            vals = pd.to_numeric(m[col], errors="coerce")
            m[col] = vals.round().clip(0, 10)
    available = [c for c in PAR_YEAR_COLS if c in m.columns]
    if available:
        m["PAR_Avg_5Y"] = m[available].mean(axis=1, skipna=True).round(2)
        m["PAR_Years_Available"] = m[available].notna().sum(axis=1)
    return m,c,a,s

MASTER, CAPACITY, ASSUMPTIONS, SPECIAL_RULES = load_data()



def display_value(v):
    """Human-friendly read-only display; never expose NaN/NaT to users."""
    if v is None:
        return "Not available"
    try:
        if pd.isna(v):
            return "Not available"
    except Exception:
        pass
    if isinstance(v, pd.Timestamp):
        return v.strftime("%d %b %Y")
    s = str(v).strip()
    if s.lower() in {"nan","nat","none",""}:
        return "Not available"
    return s

def normalise_officer_id(v):
    try:
        n = int(float(str(v).strip()))
        return f"{n:04d}" if 1 <= n <= 5000 else None
    except Exception:
        return None


def cycle_cutoff(cycle): return pd.Timestamp(year=int(cycle), month=3, day=31)

def annual_tenure(join_date, cycle):
    d = pd.Timestamp(join_date)
    return np.nan if pd.isna(d) else int(cycle) - int(d.year)

def current_threshold(o):
    c = str(o.get("Current_Centre", ""))
    if c in ZONES[1]:
        return 4 if str(o.get("NER_Extension_Approved","No"))=="Yes" else 3
    if c == "Mumbai":
        return 10 if str(o.get("First_Mumbai_Posting","No"))=="Yes" else 5
    return 5

def destination_threshold(centre, o):
    if centre in ZONES[1]: return 3
    if centre == "Mumbai": return 10 if str(o.get("First_Mumbai_Posting","No"))=="Yes" else 5
    return 5

def min_service_for(o):
    g=str(o.get("Grade","")); r=str(o.get("Recruitment_Mode",""))
    if g=="A": return 3
    if g=="B" and r=="Direct": return 1
    if g=="B" and r=="Merit": return 7
    return {"C":7,"D":17,"E":22,"F":25}.get(g,np.nan)

def service_valid(o):
    try: sv=float(o.get("Years_of_Service",0) or 0)
    except: sv=0
    mn=min_service_for(o)
    return (np.isnan(mn) or sv>=mn),mn,sv

def policy_engine(o, cycle):
    grade=str(o.get("Grade","")).strip(); cadre=str(o.get("Cadre","")).strip(); recruit=str(o.get("Recruitment_Mode","")).strip()
    tenure=annual_tenure(o.get("Centre_Joining_Date"),cycle)
    remaining=float(o.get("Remaining_Service_Years",999) or 999)
    ner_req=str(o.get("NER_Extension_Requested","No")); ner_app=str(o.get("NER_Extension_Approved","No"))
    special=str(o.get("Special_Exemption","None")); special_sub=str(o.get("Special_Request_Submitted","No"))
    valid,mn,sv=service_valid(o)
    if not valid: return {"status":"DATA_VALIDATION_FAIL","tenure":tenure,"threshold":None,"reason":f"Minimum-service assumption not met: {sv:.1f} years recorded; {mn}+ required.","review":True,"last_choice":False}
    if recruit=="Direct": return {"status":"DIRECT_RECRUIT_FIRST_POSTING","tenure":tenure,"threshold":None,"reason":"Grade B direct recruits use a separate first-posting/cold-start path.","review":True,"last_choice":False}
    if grade=="F": return {"status":"POLICY_EXCLUDED_FROM_CENTRE_TENURE_RULE","tenure":None,"threshold":None,"reason":"Grade F is excluded from centre-tenure/placement provisions.","review":True,"last_choice":False}
    if cadre in SPECIALIST: return {"status":"SPECIALIST_CADRE_ADMINISTRATIVE_REVIEW","tenure":tenure,"threshold":current_threshold(o),"reason":"Specialist cadre is planned separately; replacement must be same cadre + same grade.","review":True,"last_choice":False}
    if special in {"Sportsperson","PwBD_Caregiver"}: return {"status":"ROUTINE_TRANSFER_EXEMPTION","tenure":tenure,"threshold":None,"reason":"Routine transfer exemption; human review remains required.","review":True,"last_choice":False}
    if remaining < 2 and grade in ["A","B","C","D","E"]:
        threshold = current_threshold(o)
        reason = f"Tenure at 31 March {cycle}: {tenure} years; applicable threshold: {threshold} years. The officer is not due for routine transfer. Remaining service is {remaining:.2f} years, below the 2-year retirement-protection threshold; human review is required to confirm the applicable retirement protection and any exception."
        return {"status":"NORMALLY_NOT_TRANSFERRED_<2Y_TO_RETIREMENT","tenure":tenure,"threshold":threshold,"reason":reason,"review":True,"last_choice":False}
    if str(o.get("Current_Centre","")) in ZONES[1] and ner_req=="Yes" and ner_app!="Yes":
        return {"status":"HUMAN_REVIEW_NER_EXTENSION","tenure":tenure,"threshold":3,"reason":"NER extension was requested but not approved; human review required.","review":True,"last_choice":False}
    threshold = 4 if str(o.get("Current_Centre","")) in ZONES[1] and ner_app=="Yes" else current_threshold(o)
    due = tenure >= threshold
    last_choice = due and remaining > 2 and remaining <= 5
    status = "ROUTINE_TRANSFER_DUE" if due else "NOT_ROUTINE_TRANSFER_DUE"
    review = bool(special_sub=="Yes" or last_choice)
    reason=f"Tenure at 31 March {cycle}: {tenure} years; applicable threshold: {threshold} years."
    if last_choice: reason += " Final-posting choice assumption applies; preference should be honoured subject to capacity and administrative review."
    if special_sub=="Yes": reason += " Special request submitted; human review required."
    return {"status":status,"tenure":tenure,"threshold":threshold,"reason":reason,"review":review,"last_choice":last_choice}

def validate_prefs(prefs, grade):
    errs=[]
    if len(set(prefs)) != 5: errs.append("Exactly five unique preferences are required for this prototype.")
    if grade in ["A","B","C"]:
        z=[CENTRE_ZONE[p] for p in prefs if p in CENTRE_ZONE]
        if any(z.count(x)>2 for x in set(z)): errs.append("No more than two choices may be from one zone for the annual-choice rule.")
    return errs

def preference_rank(prefs,c): return prefs.index(c)+1 if c in prefs else 99

def base_capacity():
    cap=CAPACITY.copy()
    cap["Vacancies_Before_Transfers"]=pd.to_numeric(cap["Vacancies_Before_Transfers"],errors="coerce").fillna(0).astype(int)
    cap["Static_Slots"]=cap["Vacancies_Before_Transfers"]
    return cap

def allowed_destinations(o):
    cadre=str(o["Cadre"]); grade=str(o["Grade"])
    if cadre in SPECIALIST:
        cc=base_capacity(); allowed=set(cc[(cc.Cadre==cadre)&(cc.Grade==grade)&((cc.Current_Staff>0)|(cc.Centre=="Mumbai"))].Centre.tolist()); allowed.add("Mumbai"); return sorted(allowed)
    return ALL_CENTRES

def par_info(o):
    avg=o.get("PAR_Avg_5Y",np.nan); yrs=o.get("PAR_Years_Available",0)
    try: avg=float(avg)
    except: avg=np.nan
    try: yrs=int(yrs)
    except: yrs=0
    high=bool(pd.notna(avg) and avg>PAR_PRIORITY_THRESHOLD)
    return avg,yrs,high

def candidate_score(o, centre, prefs):
    rank=preference_rank(prefs,centre); pref=PREF_SCORE.get(rank,0)
    zone_bonus=10 if CENTRE_ZONE.get(o.get("Current_Centre"))!=CENTRE_ZONE.get(centre) else 0
    avg,_,high=par_info(o); par_bonus=PAR_WEIGHT if high else (PAR_WEIGHT*(max(0,avg-8)/2) if pd.notna(avg) else 0)
    last_bonus=20 if rank<99 and float(o.get("Remaining_Service_Years",999))<=destination_threshold(centre,o) else 0
    return float(pref+zone_bonus+par_bonus+last_bonus)

def satisfaction(rank, o, allocated=True):
    if not allocated or rank==99: base=-25
    else: base=PREF_SAT.get(rank,-25)
    avg,_,high=par_info(o)
    # bounded +/- 1–5 adjustment for model-fit/employee outcome; not a policy rule.
    adj=0
    if pd.notna(avg): adj=int(np.clip(round((avg-8.0)*2),-5,5))
    return int(np.clip(base+adj,-25,100))


def last_posting_centre(o):
    """Return the most recent prior centre from the synthetic posting-history string."""
    raw = str(o.get("Previous_Posting_History", "None recorded")).strip()
    if raw.lower() in {"none", "none recorded", "nan", ""}:
        return None
    parts = [part.strip() for part in raw.split("→") if part.strip()]
    return parts[-1] if parts else None

def candidate_table(o,prefs):
    cap=base_capacity(); rows=[]
    for centre in allowed_destinations(o):
        if centre==o["Current_Centre"]: continue
        if centre==last_posting_centre(o): continue
        rr=cap[(cap.Centre==centre)&(cap.Grade==o["Grade"])&(cap.Cadre==o["Cadre"])]
        if rr.empty: continue
        vacancy=int(rr.iloc[0]["Static_Slots"])
        rank=preference_rank(prefs,centre)
        if vacancy<=0 and centre not in prefs: continue
        rows.append({"Centre":centre,"Zone":CENTRE_ZONE[centre],"Available_Slots":vacancy,"Preference_Rank":None if rank==99 else rank,"Model_Score":round(candidate_score(o,centre,prefs),2),"Estimated_Satisfaction":satisfaction(rank,o,True) if rank<99 else None})
    return pd.DataFrame(rows).sort_values(["Preference_Rank","Model_Score"],na_position="last") if rows else pd.DataFrame()

def optimise_batch(df,prefs_map,cycle,capacity_multiplier=1.0,preference_multiplier=1.0,extra_direct_recruits=0):
    cap=base_capacity().copy()
    cap["Static_Slots"]=(cap["Static_Slots"]*capacity_multiplier).round().astype(int)
    if int(extra_direct_recruits)>0:
        idx=cap[(cap.Grade=="B")&(cap.Cadre=="CSG")].sort_values("Static_Slots",ascending=False).index.tolist()
        for j in range(int(extra_direct_recruits)):
            if idx: cap.loc[idx[j % len(idx),"Static_Slots"]]+=1
    eligible=[]; policy_rows=[]
    for _,r in df.iterrows():
        pol=policy_engine(r,cycle)
        policy_rows.append((r,pol))
        if pol["status"]=="ROUTINE_TRANSFER_DUE" and len(prefs_map.get(r["Officer_ID"],[]))==5:
            eligible.append(r)
    edf=pd.DataFrame(eligible)
    if edf.empty: return pd.DataFrame(),edf,pd.DataFrame()
    vars=[]
    # Scalability: retain all five preferences plus up to three best non-preference alternatives.
    # This keeps the whole-batch problem tractable while still giving the optimiser escape routes.
    for _,r in edf.iterrows():
        prefs=prefs_map[r["Officer_ID"]]
        scored=[]
        for centre in allowed_destinations(r):
            if centre==r["Current_Centre"]: continue
            if centre==last_posting_centre(r): continue
            rr=cap[(cap.Centre==centre)&(cap.Grade==r["Grade"])&(cap.Cadre==r["Cadre"])]
            if rr.empty: continue
            score=candidate_score(r,centre,prefs)*preference_multiplier
            scored.append((centre,score))
        preferred=[x for x in scored if x[0] in prefs]
        # Include centres that currently have same-grade/same-cadre officers in the batch;
        # these destinations can participate in valid transfer chains.
        occupied_same=set(edf[(edf.Grade==r["Grade"])&(edf.Cadre==r["Cadre"])]["Current_Centre"].tolist())
        chain_alts=sorted([x for x in scored if x[0] in occupied_same and x[0] not in prefs],key=lambda x:x[1],reverse=True)[:7]
        alternatives=sorted([x for x in scored if x[0] not in prefs and x[0] not in occupied_same],key=lambda x:x[1],reverse=True)[:3]
        selected=[]
        seen=set()
        for x in preferred+chain_alts+alternatives:
            if x[0] not in seen:
                selected.append(x); seen.add(x[0])
        for centre,score in selected:
            vars.append((r["Officer_ID"],centre,score,r["Grade"],r["Cadre"],r["Current_Centre"]))
    if not vars or not SCIPY_OK: return pd.DataFrame(),edf,pd.DataFrame()
    # Add unallocated option with strong penalty so every eligible officer receives a decision.
    for _,r in edf.iterrows(): vars.append((r["Officer_ID"],"UNALLOCATED",-5000.0,r["Grade"],r["Cadre"],r["Current_Centre"]))
    n=len(vars); c=np.array([-v[2] for v in vars],dtype=float); integ=np.ones(n); lb=np.zeros(n); ub=np.ones(n)
    row_idx=[]; col_idx=[]; data=[]; lo=[]; hi=[]; row_no=0
    for oid in edf["Officer_ID"].tolist():
        for j,v in enumerate(vars):
            if v[0]==oid: row_idx.append(row_no); col_idx.append(j); data.append(1)
        lo.append(1); hi.append(1); row_no+=1
    # Centre capacity: static vacancy + selected outgoing transfers from that same centre.
    for centre in ALL_CENTRES:
        for grade in GRADES:
            for cadre in CADRES:
                row=cap[(cap.Centre==centre)&(cap.Grade==grade)&(cap.Cadre==cadre)]
                if row.empty: continue
                static=int(row.iloc[0]["Static_Slots"])
                for j,v in enumerate(vars):
                    incoming = (v[1]==centre and v[3]==grade and v[4]==cadre)
                    outgoing = (v[5]==centre and v[3]==grade and v[4]==cadre and v[1] != "UNALLOCATED")
                    if incoming: row_idx.append(row_no); col_idx.append(j); data.append(1)
                    if outgoing: row_idx.append(row_no); col_idx.append(j); data.append(-1)
                lo.append(-np.inf); hi.append(static); row_no+=1
    A=sparse.coo_matrix((data,(row_idx,col_idx)),shape=(row_no,n)).tocsr()
    res=milp(c,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A,np.array(lo),np.array(hi)),options={"time_limit":60,"mip_rel_gap":0.03})
    if res.x is None: return pd.DataFrame(),edf,pd.DataFrame()
    chosen=[vars[i] for i,x in enumerate(res.x) if x>.5]
    rows=[]
    for _,r in edf.iterrows():
        x=next(v for v in chosen if v[0]==r["Officer_ID"])
        pol=policy_engine(r,cycle); centre=x[1]; rank=preference_rank(prefs_map[r["Officer_ID"]],centre) if centre!="UNALLOCATED" else 99
        if centre=="UNALLOCATED":
            reason="No preferred/feasible destination could be allocated within the simultaneous Centre × Grade × Cadre capacity model. Human review required."
            sat=satisfaction(99,r,False)
            rec="UNALLOCATED – HUMAN REVIEW"
        else:
            sat=satisfaction(rank,r,True)
            if rank<99:
                reason=f"Choice {rank} allotted. Satisfaction baseline {PREF_SAT[rank]}%, with a model adjustment of {sat-PREF_SAT[rank]:+d}% based on the available PAR profile."
            else:
                pref_text=", ".join([f"P{i}: {prefs_map[r['Officer_ID']][i-1]}" for i in range(1,6)])
                reason=f"None of the five choices was allotted. Preferences considered: {pref_text}. The whole-batch optimiser prioritised simultaneous Centre × Grade × Cadre feasibility, competing officers, organisational capacity and advisory score; HRMD review is required for this case."
            rec=centre
        rows.append({"Officer_ID":r["Officer_ID"],"Recommended_Centre":rec,"Recommended_Zone":CENTRE_ZONE.get(centre,""),"Preference_Rank":None if rank==99 else rank,"Employee_Satisfaction_%":sat,"Satisfaction_Adjustment_%":sat-(PREF_SAT.get(rank,-25) if rank!=99 else -25),"Grade":r["Grade"],"Cadre":r["Cadre"],"Origin_Centre":r["Current_Centre"],"PAR_Avg_5Y":r.get("PAR_Avg_5Y",np.nan),"PAR_Priority":"YES" if par_info(r)[2] else "NO","Human_Review_Flag":"Yes" if pol["review"] or rank==99 or r["Cadre"] in SPECIALIST else "No","Reason_for_Posting_Outcome":reason,"Policy_Status":pol["status"],"Allocation_Method":"Whole-batch MILP optimisation"})
    return pd.DataFrame(rows),edf,pd.DataFrame(policy_rows,columns=["Officer","Policy"])

def prepare_preferences_input(inp):
    """Accept the revised Zone→Centre template, while retaining backward compatibility."""
    centre_cols=[f"Preference_{i}_Centre" for i in range(1,6)]
    old_cols=[f"Preference_{i}" for i in range(1,6)]
    if all(c in inp.columns for c in centre_cols):
        prefs={f"Preference_{i}":inp[f"Preference_{i}_Centre"].astype(str).str.strip() for i in range(1,6)}
        for i in range(1,6):
            zc=f"Preference_{i}_Zone"
            if zc in inp.columns:
                bad=[]
                for z,c in zip(inp[zc],prefs[f"Preference_{i}"]):
                    try: bad.append(int(z) != int(CENTRE_ZONE.get(c,-1)))
                    except: bad.append(True)
                if any(bad):
                    raise ValueError(f"Preference {i}: selected Zone does not match selected Centre for one or more officers.")
        return prefs
    if all(c in inp.columns for c in old_cols):
        return {c:inp[c].astype(str).str.strip() for c in old_cols}
    raise ValueError("Input must contain either Preference_1_Centre ... Preference_5_Centre or the legacy Preference_1 ... Preference_5 columns.")

def zone_centre_inputs(prefix, default_prefs=None):
    default_prefs=default_prefs or [ALL_CENTRES[0]]*5
    prefs=[]; cols=st.columns(5)
    for i,col in enumerate(cols,1):
        with col:
            zopts=list(ZONES.keys())
            default=default_prefs[i-1] if i-1<len(default_prefs) else None
            dz=CENTRE_ZONE.get(default,1)
            z=st.selectbox(f"P{i} Zone",zopts,index=zopts.index(dz),key=f"{prefix}_z{i}")
            centres=[c for c in ZONES[z] if c != st.session_state.get("current_centre_for_prefs")]
            if default not in centres: default=centres[0]
            centre=st.selectbox(f"P{i} Centre",centres,index=centres.index(default),key=f"{prefix}_c{i}")
            prefs.append(centre)
    return prefs

def final_box(place,review,sat=None,reason=""):
    cls="review" if review else ""
    st.markdown(f'<div class="answer {cls}"><h2>FINAL TRANSFER ASSESSMENT</h2><div class="big">NEXT POSTING: {place}</div><div class="big">HUMAN REVIEW REQUIRED: {"YES" if review else "NO"}</div>{f"<div class=\"big\">EMPLOYEE SATISFACTION: {sat}%</div>" if sat is not None else ""}<div>{reason}</div></div>',unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Transfer Cycle")
    cycle=st.number_input("Transfer Cycle Year",min_value=2027,max_value=2100,value=2027,step=1)
    st.info(f"Tenure cut-off: 31 March {cycle}\n\nTransfer effective: 1 April {cycle}")
    st.caption("Synthetic capstone prototype • no live personnel data")

tab_hr,tab_emp,tab_policy=st.tabs(["HRMD CO Dashboard","Employee View","Model / Policy"])

with tab_emp:
    st.markdown('<h2 class="section">Employee Transfer View</h2>',unsafe_allow_html=True)
    st.write("Enter your Officer ID. Master information is read-only. The screen can show the result from the HRMD CO whole-batch run; it does not constitute a transfer order.")
    a,b=st.columns([4,1])
    with a: oid=st.text_input("Officer ID — 4 digits (0001–5000)",placeholder="e.g. 0001",max_chars=4,key="emp_oid")
    with b:
        st.write(""); fetch=st.button("Fetch Officer",type="primary",use_container_width=True,key="emp_fetch")
    if fetch:
        recs=MASTER[MASTER.Officer_ID==normalise_officer_id(oid)]
        if recs.empty: st.error("Officer ID not found. Enter a valid four-digit ID from 0001 to 5000."); st.session_state.pop("emp_rec",None)
        else: st.session_state["emp_rec"]=recs.iloc[0].to_dict()
    rec=st.session_state.get("emp_rec")
    if rec:
        st.markdown('<h3 class="section">Read-only officer record</h3>',unsafe_allow_html=True)
        summary=[("Officer ID","Officer_ID"),("Grade","Grade"),("Cadre","Cadre"),("Recruitment Mode","Recruitment_Mode"),("Current Centre","Current_Centre"),("Current Centre Joining Date","Centre_Joining_Date"),("Current Centre Tenure","Current_Centre_Tenure_Years"),("Applicable Tenure","Current_Centre_Required_Tenure"),("Joining Age","Joining_Age"),("Retirement Date","Retirement_Date"),("Remaining Service","Remaining_Service_Years"),("Years of Service","Years_of_Service"),("NER History","NER_History_Years"),("Mumbai Posting Count","Mumbai_Posting_Count"),("Mumbai Posting History (synthetic)","Mumbai_Posting_History"),("NER Centre History","NER_Centre_History"),("Previous Zone History","Previous_Zone_History"),("CO Posting Completed","CO_Posting_Completed"),("PAR Average (5Y)","PAR_Avg_5Y"),("PAR Priority","PAR_Priority_Flag")]
        cols=st.columns(4)
        for i,(lab,key) in enumerate(summary):
            raw=rec.get(key, "")
            val=display_value(raw)
            if key == "NER_Centre_History" and val == "Not available": val = "Nil"
            cols[i%4].metric(lab,val)
        st.markdown("**Previous posting history (full)**")
        hist=display_value(rec.get("Previous_Posting_History", ""))
        st.write("Nil" if hist == "Not available" else hist)
        st.caption("The posting-history fields in this prototype are synthetic test data, not verified historical records.")
        try:
            tenure_ok = float(rec.get("Current_Centre_Tenure_Years",0)) <= float(rec.get("Current_Centre_Required_Tenure",0))
        except Exception:
            tenure_ok = False
        st.markdown("**Current-centre tenure control:** " + ("PASS" if tenure_ok else "REVIEW REQUIRED"))
        st.markdown('<h3 class="section">Your five preferences</h3>',unsafe_allow_html=True)
        st.session_state["current_centre_for_prefs"]=rec["Current_Centre"]
        prefs=zone_centre_inputs("emp", [c for c in ["Chennai","Ahmedabad","Vijayawada","Lucknow","Imphal"] if c!=rec["Current_Centre"]][:5])
        ner_req=st.selectbox("NER Extension Requested?",["No","Yes"],key="emp_nerreq")
        ner_app=st.selectbox("NER Extension Approved?",["No","Yes"],key="emp_nerapp")
        special_ex=st.selectbox("Routine Exemption",["None","Sportsperson","PwBD_Caregiver"],key="emp_spex")
        if st.button("Check Batch Transfer Result",type="primary",key="emp_run"):
            errs=validate_prefs(prefs,rec["Grade"])
            if errs:
                for e in errs: st.error(e)
            else:
                o=dict(rec); o.update({"NER_Extension_Requested":ner_req,"NER_Extension_Approved":ner_app,"Special_Exemption":special_ex})
                pol=policy_engine(o,cycle)
                if pol["status"]!="ROUTINE_TRANSFER_DUE":
                    final_box("No routine transfer recommendation",pol["review"],None,pol["reason"])
                else:
                    # A defensible employee outcome must use the same simultaneous whole-batch plan as HRMD CO.
                    full_plan = st.session_state.get("hr_full_plan", pd.DataFrame())
                    batch_row = full_plan[full_plan.get("Officer_ID", pd.Series(dtype=str)).astype(str).str.zfill(4) == str(rec["Officer_ID"]).zfill(4)] if not full_plan.empty else pd.DataFrame()
                    st.markdown("**Batch-aware employee result**")
                    if batch_row.empty:
                        st.warning("No matching whole-batch result is available yet. HRMD CO must upload the complete office batch, run the whole-batch plan, and include this officer before an employee result can be shown. No likelihood percentage is displayed without that batch result.")
                    else:
                        br=batch_row.iloc[0]
                        place=display_value(br.get("Recommended_Centre", "No result"))
                        review=str(br.get("Human_Review_Flag", "Yes")).lower() == "yes"
                        rank=br.get("Preference_Rank", np.nan)
                        if pd.notna(rank):
                            rank_text=f"P{int(rank)}"
                        else:
                            rank_text="Not among the five preferences / no preference rank"
                        st.metric("Whole-batch recommended centre", place)
                        st.write(f"**Preference outcome:** {rank_text}")
                        st.write(f"**Policy status:** {display_value(br.get('Policy_Status', 'Not available'))}")
                        st.write(f"**Reason:** {display_value(br.get('Reason_for_Posting_Outcome', br.get('Reason', 'Not available')))}")
                        st.warning("This is the current whole-batch model output, not a transfer order. It changes if the batch, preferences, capacity or scenario settings change.")
                    st.caption("No percentage is displayed: no validated probability model or user-approved scoring weights have been specified.")


with tab_hr:
    st.markdown('<h2 class="section">HRMD CO — Executive Transfer & Workforce Dashboard</h2>',unsafe_allow_html=True)
    st.caption("Management decision support: workforce position, employee-reported sentiment (if supplied), preference demand, satisfaction proxies, staffing gaps, specialist cadres, retirement outlook and exceptions.")
    st.info("Sentiment is not inferred from an officer's grade, PAR, or preferences. Add optional self-reported fields to the batch file; missing responses are shown as not provided.")
    st.info("Officer IDs are randomly assigned identifiers. They do not encode or imply grade, cadre, seniority or designation.")
    up=st.file_uploader("Upload Batch Cycle Input — one file",type=["xlsx","csv"],key="hr_batch")
    if up:
        try:
            inp=pd.read_csv(up,dtype=str) if up.name.lower().endswith('.csv') else pd.read_excel(up,dtype=str)
            if "Officer_ID" not in inp.columns:
                st.error("Missing required column: Officer_ID")
            else:
                inp["Officer_ID"]=inp["Officer_ID"].apply(normalise_officer_id)
                merged=inp.merge(MASTER,on="Officer_ID",how="left",suffixes=("","_MASTER"))
                if merged.Grade.isna().any(): st.error("One or more Officer IDs were not found in the 5,000-record synthetic master database.")
                else:
                    for col,default in [("NER_Extension_Requested","No"),("NER_Extension_Approved","No"),("Special_Request_Submitted","No"),("Special_Request_Type","None")]:
                        if col not in merged: merged[col]=default
                    pref_cols=prepare_preferences_input(inp)
                    for k,v in pref_cols.items(): merged[k]=v.values
                    prefs_map={r.Officer_ID:[r[f"Preference_{i}"] for i in range(1,6)] for _,r in merged.iterrows()}
                    st.success(f"Matched {len(merged):,} Officer IDs to the master database.")
                    c1,c2=st.columns(2)
                    capacity_multiplier=c1.slider("What-if: centre capacity multiplier",0.90,1.20,1.00,0.01)
                    extra_direct=c2.number_input("What-if: additional Grade B direct recruits",0,500,0,10)
                    run=st.button("▶ RUN COMPLETE WHOLE-BATCH PLAN",type="primary",use_container_width=True)
                    if run:
                        screen_rows=[]
                        for _,r in merged.iterrows():
                            pol=policy_engine(r,cycle)
                            screen_rows.append({"Officer_ID":r.Officer_ID,"Grade":r.Grade,"Cadre":r.Cadre,"Recruitment_Mode":r.Recruitment_Mode,"Current_Centre":r.Current_Centre,"Current_Centre_Joining_Date":r.Centre_Joining_Date,"Current_Centre_Tenure":r.Current_Centre_Tenure_Years,"Required_Tenure":pol["threshold"],"Policy_Status":pol["status"],"PAR_Avg_5Y":r.get("PAR_Avg_5Y",np.nan),"PAR_Priority":"YES" if par_info(r)[2] else "NO","Reason":pol["reason"],"Human_Review_Flag":"Yes" if pol["review"] else "No"})
                        screen=pd.DataFrame(screen_rows)
                        final,eligible,_=optimise_batch(merged,prefs_map,cycle,capacity_multiplier,1.0,extra_direct)
                        # Full decision register: every officer in the uploaded batch, not only transfer-due officers.
                        if not final.empty:
                            full_plan=screen.merge(final.drop(columns=[c for c in ["Grade","Cadre","Policy_Status"] if c in final.columns]),on="Officer_ID",how="left")
                        else:
                            full_plan=screen.copy()
                        full_plan["Recommended_Centre"]=full_plan.get("Recommended_Centre",pd.Series(index=full_plan.index,dtype=object)).fillna(full_plan["Policy_Status"].map(lambda x: "SEPARATE FIRST-POSTING PATH" if x=="DIRECT_RECRUIT_FIRST_POSTING" else "NO ROUTINE TRANSFER"))
                        st.session_state["hr_screen"]=screen; st.session_state["hr_final"]=final; st.session_state["hr_full_plan"]=full_plan; st.session_state["hr_eligible"]=eligible
                    if "hr_screen" in st.session_state:
                        screen=st.session_state["hr_screen"]; final=st.session_state.get("hr_final",pd.DataFrame()); full_plan=st.session_state.get("hr_full_plan",screen.copy()); eligible=st.session_state.get("hr_eligible",pd.DataFrame())
                        # Executive KPIs
                        st.markdown('<h3 class="section">Executive outcome</h3>',unsafe_allow_html=True)
                        allocated=final[final.Recommended_Centre.str.startswith("UNALLOCATED")==False] if not final.empty else pd.DataFrame()
                        k=st.columns(6)
                        k[0].metric("Officers in input",f"{len(merged):,}")
                        k[1].metric("Transfer-due",f"{len(eligible):,}")
                        k[2].metric("Allocated",f"{len(allocated):,}")
                        k[3].metric("Human review",f"{int((final.Human_Review_Flag=='Yes').sum()) if not final.empty else 0:,}")
                        k[4].metric("Avg satisfaction",f"{allocated['Employee_Satisfaction_%'].mean():.1f}%" if not allocated.empty else "—")
                        k[5].metric("P1 achieved",f"{int((allocated.Preference_Rank==1).sum())/len(allocated)*100:.1f}%" if not allocated.empty else "—")
                        st.markdown('<h3 class="section">Final plan — HRMD decision view</h3>',unsafe_allow_html=True)
                        if final.empty: st.error("No allocation result was generated. Verify SciPy and the input/capacity data.")
                        else:
                            st.dataframe(final,use_container_width=True,hide_index=True)
                            bio=io.BytesIO()
                            with pd.ExcelWriter(bio,engine="openpyxl") as xw:
                                full_plan.to_excel(xw,index=False,sheet_name="Final_Decision_Register")
                                final.to_excel(xw,index=False,sheet_name="Transfer_Allocations")
                                screen.to_excel(xw,index=False,sheet_name="Policy_Screening")
                            st.download_button("Download HRMD Final Plan + Screening",bio.getvalue(),"TMD3_HRMD_Final_Transfer_Plan.xlsx")
                            st.markdown('<h3 class="section">8. HRMD CO management dashboards</h3>',unsafe_allow_html=True)
                            d1,d2,d3,d4=st.tabs(["Centre Manpower","Grade & Recruitment","Cadre Gaps","Retirement Outlook"])
                            with d1:
                                centre=MASTER.groupby("Current_Centre").size().rename("Opening_Staff").reset_index()
                                out=final[final["Recommended_Centre"].astype(str).str.startswith("UNALLOCATED")==False].groupby("Origin_Centre").size().rename("Transfer_Out").reset_index() if not final.empty else pd.DataFrame(columns=["Origin_Centre","Transfer_Out"])
                                inc=allocated.groupby("Recommended_Centre").size().rename("Transfer_In").reset_index() if not allocated.empty else pd.DataFrame(columns=["Recommended_Centre","Transfer_In"])
                                cc=centre.merge(out,left_on="Current_Centre",right_on="Origin_Centre",how="left").merge(inc,left_on="Current_Centre",right_on="Recommended_Centre",how="left").fillna(0)
                                for col in ["Opening_Staff","Transfer_Out","Transfer_In"]: cc[col]=cc[col].astype(int)
                                cc["Closing_Staff"]=cc.Opening_Staff-cc.Transfer_Out+cc.Transfer_In
                                cc=cc.sort_values("Current_Centre")
                                st.caption(f"All {len(cc)} centres shown. Opening staffing is calculated from the reconciled 5,000-record synthetic officer master.")
                                st.dataframe(cc[["Current_Centre","Opening_Staff","Transfer_Out","Transfer_In","Closing_Staff"]],use_container_width=True,hide_index=True,height=650)
                                st.markdown("**Centre-wise grade distribution (opening staff)**")
                                grade_dist=pd.crosstab(MASTER["Current_Centre"],MASTER["Grade"]).reindex(columns=GRADES,fill_value=0).reset_index()
                                grade_dist["Total"]=grade_dist[GRADES].sum(axis=1)
                                st.dataframe(grade_dist.sort_values("Current_Centre"),use_container_width=True,hide_index=True,height=650)
                                st.caption("This distribution uses the same officer master as the employee lookup and whole-batch planner; it is not read from an unreconciled raw grade-cell table.")
                            with d2:
                                gr=MASTER.groupby(["Grade","Recruitment_Mode"]).size().reset_index(name="Current_Staff")
                                ret=MASTER.groupby("Grade").Expected_Retirement_This_Cycle.apply(lambda x:(x=="Yes").sum()).reset_index(name="Expected_Retirements")
                                st.dataframe(gr.merge(ret,on="Grade",how="left"),use_container_width=True,hide_index=True)
                                st.info("Workforce assumption: retirements are replaced by Grade A merit promotions and Grade B direct recruits in the synthetic planning scenario; exact recruitment mix remains a management assumption.")
                            with d3:
                                st.markdown("**Specialist cadre position**")
                                st.dataframe(SPECIAL_RULES,use_container_width=True,hide_index=True)
                            with d4:
                                ro=MASTER[MASTER.Expected_Retirement_This_Cycle=="Yes"].groupby(["Grade","Cadre"]).size().reset_index(name="Retirements_This_Cycle")
                                st.dataframe(ro,use_container_width=True,hide_index=True)
                                st.info("This view supports forward workforce planning: retirement pressure can be compared with planned entry through Grade A merit promotion and Grade B direct recruitment.")
                                st.markdown("**PAR distribution and priority pool**")
                                par_frames=[]
                                for pc in PAR_YEAR_COLS:
                                    if pc in MASTER.columns:
                                        tmp=MASTER[pc].dropna().astype(int)
                                        par_frames.append(pd.DataFrame({"Year":pc.replace("PAR_",""),"PAR_Mark":tmp}))
                                if par_frames:
                                    pv=pd.concat(par_frames,ignore_index=True)
                                    dist=pv["PAR_Mark"].value_counts().sort_index().rename_axis("PAR_Mark").reset_index(name="Count")
                                    dist["% of available annual ratings"]=(dist["Count"]/dist["Count"].sum()*100).round(1)
                                    st.dataframe(dist,use_container_width=True,hide_index=True)
                                pstat=MASTER["PAR_Avg_5Y"].dropna()
                                st.metric("Average PAR > 9 priority pool",f"{(pstat>9).mean()*100:.1f}%")
                                st.caption("Annual marks are rounded to whole numbers; five-year averages may be decimal. The distribution is a synthetic testing assumption.")
                            st.markdown('<h3 class="section">9. HRMD CO — What-if Analysis</h3>',unsafe_allow_html=True)
                            st.write("Change the scenario controls above and rerun the plan. The scenario is a planning experiment, not a policy instruction.")
                            st.markdown("**Useful scenarios:** increase/decrease centre capacity; test additional Grade B direct recruits; compare average satisfaction, P1 achievement, unallocated officers and human-review cases.")
                            st.markdown('<h3 class="section">Employee preference and exception analysis</h3>',unsafe_allow_html=True)
                            if not allocated.empty:
                                sat=allocated["Preference_Rank"].fillna(99).value_counts().sort_index().rename_axis("Preference").reset_index(name="Officers")
                                sat["Satisfaction_Band"]=[PREF_SAT.get(int(x),-25) for x in sat.Preference]
                                st.markdown("**Actual allocation by preference rank**")
                                st.dataframe(sat,use_container_width=True,hide_index=True)
                            pref_rows=[]
                            for rank in range(1,6):
                                col=f"Preference_{rank}"
                                if col in merged.columns:
                                    for centre_name,count in merged[col].astype(str).value_counts().items():
                                        if centre_name and centre_name.lower() not in {"nan","none",""}:
                                            pref_rows.append({"Preference_Rank":f"P{rank}","Preferred_Centre":centre_name,"Officers_Selecting":int(count)})
                            if pref_rows:
                                demand=pd.DataFrame(pref_rows).sort_values(["Preference_Rank","Officers_Selecting"],ascending=[True,False])
                                st.markdown("**Preferred choices summary — submitted demand by rank**")
                                st.dataframe(demand,use_container_width=True,hide_index=True)
                                st.download_button("Download preference-demand summary",demand.to_csv(index=False).encode("utf-8"),"TMD3_Preferred_Choices_Summary.csv","text/csv")
                            if "Employee_Sentiment" in merged.columns:
                                sent=merged["Employee_Sentiment"].fillna("Not provided").astype(str).str.strip().replace({"":"Not provided","nan":"Not provided"})
                                st.markdown("**Employee-reported sentiment**")
                                sm=sent.value_counts().rename_axis("Sentiment").reset_index(name="Officers")
                                sm["Share_%"]=(sm.Officers/len(merged)*100).round(1)
                                st.dataframe(sm,use_container_width=True,hide_index=True)
                                if "Sentiment_Comment" in merged.columns:
                                    comments=merged.loc[sent.str.lower()!="not provided",["Officer_ID","Current_Centre","Grade","Employee_Sentiment","Sentiment_Comment"]].copy()
                                    st.markdown("**Comments for authorised HR review**")
                                    st.dataframe(comments,use_container_width=True,hide_index=True)
                            else:
                                st.warning("No employee sentiment responses were supplied. Add Employee_Sentiment and optional Sentiment_Comment columns to the batch input.")
                            reasons=final[final.Human_Review_Flag=="Yes"]["Reason_for_Posting_Outcome"].value_counts().reset_index(name="Cases").rename(columns={"index":"Reason"})
                            st.markdown("**Human-review and exception queue**")
                            st.dataframe(reasons,use_container_width=True,hide_index=True)
                            action=final[(final["Preference_Rank"].fillna(99)>2) | (final["Human_Review_Flag"]=="Yes")].copy()
                            if not action.empty:
                                st.markdown("**CO action queue — lower preferences or human review**")
                                st.dataframe(action[["Officer_ID","Grade","Cadre","Origin_Centre","Recommended_Centre","Preference_Rank","Human_Review_Flag","Reason_for_Posting_Outcome"]],use_container_width=True,hide_index=True)
        except Exception as e:
            st.error(f"Could not process the batch file: {e}")

with tab_policy:
    st.markdown('<h2 class="section">Model / Policy — Assumptions, Controls & Auditability</h2>',unsafe_allow_html=True)
    st.info("This is a synthetic capstone prototype. RBI policy determines eligibility and constraints; optimisation recommends allocations; HRMD/competent authority retains final decision-making.")
    st.markdown('<h3 class="section">Employee satisfaction model</h3>',unsafe_allow_html=True)
    st.table(pd.DataFrame({"Outcome":["Choice 1","Choice 2","Choice 3","Choice 4","Choice 5","None of five choices"],"Base satisfaction %":[100,75,50,25,50,-25],"Model adjustment":"±1–5%"}))
    st.caption("These satisfaction values and PAR adjustments are prototype assumptions, not RBI policy or user-specified rules. They are not probabilities and should not be treated as validated measures of actual employee satisfaction.")
    st.markdown('<h3 class="section">Performance / PAR assumptions</h3>',unsafe_allow_html=True)
    st.write("Each annual PAR mark is a **whole-number rating from 0 to 10**. The average of the available last five annual marks may be a decimal and is used for the advisory performance score.")
    st.write("Synthetic annual distribution target: approximately **5% score 10, 30% score 9, 60% score 8 and 5% score 7**. This is a synthetic data-generation assumption, not an RBI rule.")
    st.write(f"The current prototype code gives an average PAR rating above {PAR_PRIORITY_THRESHOLD:.1f}/10 an advisory weight of {PAR_WEIGHT:.0f} points. This was not specified by you; it is an unapproved prototype assumption and should be confirmed or removed before relying on allocation results.")
    st.markdown('<h3 class="section">Core assumptions</h3>',unsafe_allow_html=True)
    st.dataframe(ASSUMPTIONS,use_container_width=True,hide_index=True)
    st.markdown('<h3 class="section">Specialist cadre rules</h3>',unsafe_allow_html=True)
    st.dataframe(SPECIAL_RULES,use_container_width=True,hide_index=True)
    st.markdown('<h3 class="section">Management outputs</h3>',unsafe_allow_html=True)
    st.markdown("""
- **Final posting decision:** next centre, preference achieved, satisfaction, human-review flag and reason.
- **Employee view:** displays the officer’s result from the same whole-batch allocation used by HRMD CO. No probability percentage is shown because the existing heuristic score weights were not supplied or validated as probabilities.
- **HRMD CO dashboard:** centre manpower, preference demand by rank, employee-reported sentiment (if provided), satisfaction proxies, retirement outlook, exceptions and CO action queue.
- **What-if analysis:** capacity and recruitment scenarios.
- **Workforce planning:** opening/closing strength, retirement pressure and replacement planning.
- **Explainability:** reason for every non-preference allocation.
- **Auditability:** policy status, data source, allocation method and human-review flags.
""")
    st.markdown('<h3 class="section">Important policy controls</h3>',unsafe_allow_html=True)
    st.markdown("""
- Officer IDs are **0001–5000**.
- Grade B recruitment mode is **Direct or Merit**; Grade A is the internal Merit-channel entry level in this prototype.
- Ordinary transfer matching is **same Grade + same Cadre**.
- Specialist cadres are **DEPR, DSIM, Legal and Rajbhasha**; specialist replacement remains same cadre + same grade.
- Current-centre tenure is validated against the applicable centre rule.
- NER history is represented in whole years; approved NER extension is capped at **1 year** in the synthetic prototype.
- At least **10%** of the synthetic population has a special request.
- Joining age assumption: **23–27**; retirement age: **60**.
- Final posting before retirement follows the officer's choice subject to capacity and human/administrative review.
- Whole-batch allocation is simultaneous; it does not reserve vacancies officer-by-officer.
""")
    st.markdown('<h3 class="section">Policy source boundaries</h3>',unsafe_allow_html=True)
    st.write("The RBI Master Circular supports the normal 5-year centre tenure, first Mumbai 10-year tenure, NER 3-year tenure extendable up to 6 years at officer request, annual choice provisions and administrative-convenience/human review principles. The satisfaction scores, PAR priority weighting, 5,001-record synthetic synthetic workforce, specialist-cadre placement assumptions and scenario controls are prototype assumptions, not statements of RBI policy.")
