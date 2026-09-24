"""Build the public SDK contract and audit every SDK HTTP method against Go routes."""
import argparse, ast, inspect, json, re
from pathlib import Path
from trendsagi import models

parser=argparse.ArgumentParser()
parser.add_argument("--saas",type=Path,required=True)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
backend=(args.saas/"go_services/api_server/main.go").read_text()
normalize=lambda path:re.sub(r"\{[^}]*\}","{}",path)
routes={(method,normalize(path)) for method,path in re.findall(r'HandleFunc\("(GET|POST|PUT|DELETE|PATCH) ([^" ]+)',backend)}
for path in re.findall(r'HandleFunc\("(/[^" ]+)"',backend):
    routes.add(("GET",normalize(path)))
schemas={}
for name,model in inspect.getmembers(models,inspect.isclass):
    if model.__module__!=models.__name__ or not hasattr(model,"model_json_schema"):continue
    schema=model.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas.update(schema.pop("$defs",{}))
    schemas[name]=schema

def response_schema(annotation):
    if isinstance(annotation,ast.Attribute) and isinstance(annotation.value,ast.Name) and annotation.value.id=="models":
        return {"$ref":"#/components/schemas/"+annotation.attr}
    if isinstance(annotation,ast.Subscript) and isinstance(annotation.value,ast.Name):
        inner=response_schema(annotation.slice)
        if annotation.value.id=="List":return {"type":"array","items":inner}
        if annotation.value.id=="Optional":return {"anyOf":[inner,{"type":"null"}]}
    if isinstance(annotation,ast.Name) and annotation.id=="str":return {"type":"string"}
    return {}

paths={};audit=[];unavailable={"get_financial_data"}
tree=ast.parse((root/"src/trendsagi/client.py").read_text())
for function in ast.walk(tree):
    if not isinstance(function,ast.FunctionDef) or function.name.startswith("_"):continue
    for call in ast.walk(function):
        if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Attribute) or call.func.attr!="_request" or len(call.args)<2:continue
        if not isinstance(call.args[0],ast.Constant):continue
        method=call.args[0].value
        value=call.args[1]
        if isinstance(value,ast.Constant):path=value.value
        elif isinstance(value,ast.JoinedStr):
            path="".join(v.value if isinstance(v,ast.Constant) else "{"+ast.unparse(v.value)+"}" for v in value.values)
        else:continue
        if (method,normalize(path)) not in routes:raise SystemExit("Unregistered route: "+method+" "+path)
        audit.append({"method":function.name,"http_method":method,"path":path,"state":"unavailable" if function.name in unavailable else "registered"})
        if function.name in unavailable:continue
        # Normalize event path identifiers for a single interoperable contract.
        path=path.replace("{event_id}","{id}")
        operation={"operationId":function.name,"summary":(ast.get_docstring(function) or function.name).splitlines()[0],
            "security":[{"ApiKey":[]}],"responses":{
                "200":{"description":"Success","content":{"application/json":{"schema":response_schema(function.returns)}}},
                "401":{"description":"Authentication required"},"403":{"description":"Permission or entitlement denied"},
                "404":{"description":"Resource not found or not owned"},"409":{"description":"Current state/evidence conflict"},
                "429":{"description":"Usage limit reached"},"503":{"description":"Capability or dependency unavailable"}}}
        params=[]
        for name in re.findall(r"\{([^}]+)\}",path):
            params.append({"name":name,"in":"path","required":True,"schema":{"type":"string" if name in ("slug","task_id") else "integer"}})
        if params:operation["parameters"]=params
        if method in ("POST","PUT","PATCH"):
            operation["requestBody"]={"required":False,"content":{"application/json":{"schema":{"type":"object"}}}}
        paths.setdefault(path,{})[method.lower()]=operation

event_path="/api/intelligence/crisis-events"
params=[]
for name,values in {"status":["all","active","acknowledged","archived"],"severity":["all","low","medium","high","critical"],
 "period":["1h","24h","7d","30d","custom"],"source":["all","x","usgs","environment_agency"],
 "freshness":["all","fresh","stale","missing"],"review_status":["all","unreviewed","unconfirmed","supported","disputed","needs_review"]}.items():
    params.append({"name":name,"in":"query","schema":{"type":"string","enum":values}})
for name in ("keyword","location","startDate","endDate","timeRange"):
    params.append({"name":name,"in":"query","schema":{"type":"string"}})
params.extend([{"name":"limit","in":"query","schema":{"type":"integer","minimum":1,"maximum":100,"default":20}},
 {"name":"offset","in":"query","schema":{"type":"integer","minimum":0,"default":0}}])
paths[event_path]["get"]["parameters"]=params
review=paths[event_path+"/{id}/reviews"]["post"]
review["requestBody"]={"required":True,"content":{"application/json":{"schema":{"type":"object","additionalProperties":False,
 "required":["assessment","rationale","evidence_version"],"properties":{
 "assessment":{"type":"string","enum":["unconfirmed","supported","disputed"]},
 "rationale":{"type":"string","minLength":1,"maxLength":2000},
 "evidence_version":{"type":"string","pattern":"^[0-9a-f]{32}$"}}}}}}
review["responses"]["201"]=review["responses"].pop("200")
export=paths[event_path+"/{id}/export"]["get"]
export["parameters"].append({"name":"format","in":"query","schema":{"type":"string","enum":["json","html"],"default":"json"}})
export["responses"]["200"]["content"]={"application/json":{"schema":{"$ref":"#/components/schemas/CrisisEvent"}},"text/html":{"schema":{"type":"string"}}}
paths["/api/intelligence/resilience-settings"]["put"]["requestBody"]={"required":True,"content":{"application/json":{"schema":{
 "type":"object","additionalProperties":False,"required":["location_query"],"properties":{"location_query":{"type":"string","maxLength":120}}}}}}
# Small unauthenticated projection, never the authenticated event shape.
paths["/api/v1/public/demo-signals"]={"get":{"operationId":"get_public_demo_signals","summary":"Public, cached, dated demonstration projection",
 "security":[],"parameters":[{"in":"query","name":"mode","schema":{"type":"string","enum":["paid-media","resilience"]}}],
 "responses":{"200":{"description":"Public observations; may be empty","content":{"application/json":{"schema":{
 "type":"object","required":["signals","mode","fetched_at","schema_version"],"properties":{"mode":{"type":"string"},"schema_version":{"const":"1"},"fetched_at":{"type":"string","format":"date-time"},"signals":{"type":"array","maxItems":3,"items":{"type":"object","required":["title","source_url","source","observed_at","freshness","limitations"],"properties":{"title":{"type":"string"},"source_url":{"type":"string","format":"uri"},"source":{"type":"string"},"observed_at":{"type":"string","format":"date-time"},"freshness":{"enum":["fresh","stale"]},"limitations":{"type":"string"}}}}}}}}},"503":{"description":"Unavailable"}}}}
spec={"openapi":"3.1.0","info":{"title":"TrendsAGI public SDK API","version":"0.10.0",
 "description":"Supported SDK HTTP routes. Resilience is beta. Schemas preserve legacy optional fields; opaque older request bodies are detailed in the human API reference. No internal admin routes."},
 "servers":[{"url":"https://api.trendsagi.com"},{"url":"https://staging-api.trendsagi.com"}],
 "components":{"securitySchemes":{"ApiKey":{"type":"apiKey","in":"header","name":"X-API-Key"}},"schemas":schemas},"paths":paths}
for output in (root/"docs/openapi.json",args.saas/"docs/openapi.json",args.saas/"frontend_public/public/openapi.json"):
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(spec,indent=2)+"\n")
(root/"docs/CONTRACT_AUDIT.json").write_text(json.dumps(audit,indent=2)+"\n")
print("Audited",len(audit),"SDK HTTP calls;",len(paths),"supported contract paths.")
