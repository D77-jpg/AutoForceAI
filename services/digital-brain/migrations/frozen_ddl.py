"""Generated immutable DDL snapshot for Alembic revisions 0001/0002.

Do not hand-edit or import application ORM metadata here.
"""

PHASE1_SQLITE_UP = ('CREATE TABLE llm_request_logs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\ttrace_id VARCHAR, \n'
 '\tuser_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tmodel VARCHAR, \n'
 '\tinput_tokens INTEGER, \n'
 '\toutput_tokens INTEGER, \n'
 '\ttotal_tokens INTEGER, \n'
 '\tlatency_ms INTEGER, \n'
 '\tstatus VARCHAR, \n'
 '\terror_msg TEXT, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id)\n'
 ')',
 'CREATE INDEX ix_llm_request_logs_id ON llm_request_logs (id)',
 'CREATE INDEX ix_llm_request_logs_trace_id ON llm_request_logs (trace_id)',
 'CREATE INDEX ix_llm_request_logs_user_id ON llm_request_logs (user_id)',
 'CREATE TABLE organizations (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tinvite_code VARCHAR, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id)\n'
 ')',
 'CREATE INDEX ix_organizations_id ON organizations (id)',
 'CREATE UNIQUE INDEX ix_organizations_invite_code ON organizations (invite_code)',
 'CREATE UNIQUE INDEX ix_organizations_name ON organizations (name)',
 'CREATE TABLE knowledge_bases (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\tis_public BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_knowledge_bases_id ON knowledge_bases (id)',
 'CREATE INDEX ix_knowledge_bases_name ON knowledge_bases (name)',
 'CREATE TABLE leads (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tsource VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\temail VARCHAR, \n'
 '\tname VARCHAR, \n'
 '\tcompany VARCHAR, \n'
 '\tcountry VARCHAR, \n'
 '\tphone VARCHAR, \n'
 '\tproducts VARCHAR, \n'
 '\tintent_json JSON, \n'
 '\tconversation TEXT, \n'
 '\tsession_uuid VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_leads_email ON leads (email)',
 'CREATE INDEX ix_leads_id ON leads (id)',
 'CREATE INDEX ix_leads_organization_id ON leads (organization_id)',
 'CREATE INDEX ix_leads_session_uuid ON leads (session_uuid)',
 'CREATE INDEX ix_leads_source ON leads (source)',
 'CREATE INDEX ix_leads_status ON leads (status)',
 'CREATE TABLE llm_providers (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tbase_url VARCHAR, \n'
 '\tapi_key VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_llm_providers_id ON llm_providers (id)',
 'CREATE INDEX ix_llm_providers_name ON llm_providers (name)',
 'CREATE TABLE quality_rules (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tweight FLOAT, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_quality_rules_id ON quality_rules (id)',
 'CREATE INDEX ix_quality_rules_name ON quality_rules (name)',
 'CREATE TABLE rag_configs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\ttop_k INTEGER, \n'
 '\tscore_threshold FLOAT, \n'
 '\tchunk_size INTEGER, \n'
 '\tchunk_overlap INTEGER, \n'
 '\tsensitive_words TEXT, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_rag_configs_id ON rag_configs (id)',
 'CREATE TABLE users (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tusername VARCHAR, \n'
 '\tnickname VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\temail VARCHAR, \n'
 '\thashed_password VARCHAR, \n'
 '\twechat_openid VARCHAR, \n'
 '\twechat_unionid VARCHAR, \n'
 '\tphone VARCHAR, \n'
 '\tbio TEXT, \n'
 '\trole VARCHAR, \n'
 '\torganization_id INTEGER, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE UNIQUE INDEX ix_users_email ON users (email)',
 'CREATE INDEX ix_users_id ON users (id)',
 'CREATE UNIQUE INDEX ix_users_username ON users (username)',
 'CREATE UNIQUE INDEX ix_users_wechat_openid ON users (wechat_openid)',
 'CREATE UNIQUE INDEX ix_users_wechat_unionid ON users (wechat_unionid)',
 'CREATE TABLE bots (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\tsystem_prompt TEXT, \n'
 '\twelcome_message VARCHAR, \n'
 '\tmodel_name VARCHAR, \n'
 '\ttemperature FLOAT, \n'
 '\tkb_id INTEGER, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(kb_id) REFERENCES knowledge_bases (id)\n'
 ')',
 'CREATE INDEX ix_bots_id ON bots (id)',
 'CREATE INDEX ix_bots_name ON bots (name)',
 'CREATE TABLE brain_sessions (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\torganization_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_brain_sessions_id ON brain_sessions (id)',
 'CREATE TABLE geo_watch_queries (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\ttarget_brand VARCHAR NOT NULL, \n'
 '\t"query" VARCHAR NOT NULL, \n'
 '\tengine_name VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tinterval_hours INTEGER, \n'
 '\tenabled BOOLEAN, \n'
 '\tlast_run_at DATETIME, \n'
 '\tnext_run_at DATETIME, \n'
 '\tlast_task_id INTEGER, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_geo_watch_queries_id ON geo_watch_queries (id)',
 'CREATE INDEX ix_geo_watch_queries_target_brand ON geo_watch_queries (target_brand)',
 'CREATE INDEX ix_geo_watch_queries_user_id ON geo_watch_queries (user_id)',
 'CREATE TABLE knowledge_docs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tkb_id INTEGER, \n'
 '\tfilename VARCHAR, \n'
 '\tfile_path VARCHAR, \n'
 '\tfile_type VARCHAR, \n'
 '\tfile_size INTEGER, \n'
 '\tstatus VARCHAR, \n'
 '\terror_msg TEXT, \n'
 '\tchunk_count INTEGER, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(kb_id) REFERENCES knowledge_bases (id)\n'
 ')',
 'CREATE INDEX ix_knowledge_docs_id ON knowledge_docs (id)',
 'CREATE TABLE llm_models (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tprovider_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdisplay_name VARCHAR, \n'
 '\ttype VARCHAR, \n'
 '\tcontext_window VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tsupports_geo BOOLEAN, \n'
 '\tsupports_chat BOOLEAN, \n'
 '\tapi_key VARCHAR, \n'
 '\tbase_url VARCHAR, \n'
 '\tis_default BOOLEAN, \n'
 '\tis_kb_search_default BOOLEAN, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(provider_id) REFERENCES llm_providers (id)\n'
 ')',
 'CREATE INDEX ix_llm_models_id ON llm_models (id)',
 'CREATE UNIQUE INDEX ix_llm_models_name ON llm_models (name)',
 'CREATE TABLE marketing_contents (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tcontent_type VARCHAR, \n'
 '\tproduct_name VARCHAR, \n'
 '\tselling_points TEXT, \n'
 '\tlanguage VARCHAR, \n'
 '\ttitle VARCHAR, \n'
 '\tbody TEXT, \n'
 '\ttags JSON, \n'
 '\timage_url VARCHAR, \n'
 '\tprompt TEXT, \n'
 '\textra JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_marketing_contents_content_type ON marketing_contents (content_type)',
 'CREATE INDEX ix_marketing_contents_id ON marketing_contents (id)',
 'CREATE INDEX ix_marketing_contents_user_id ON marketing_contents (user_id)',
 'CREATE TABLE projects (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdomain VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tcompetitors JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_projects_id ON projects (id)',
 'CREATE INDEX ix_projects_name ON projects (name)',
 'CREATE TABLE analysis_tasks (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\ttarget_brand VARCHAR, \n'
 '\t"query" VARCHAR, \n'
 '\tengine_name VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tis_mentioned BOOLEAN, \n'
 '\trank_position INTEGER, \n'
 '\tsentiment_score FLOAT, \n'
 '\treasoning TEXT, \n'
 '\tcitations JSON, \n'
 '\tsuggestions JSON, \n'
 '\traw_response TEXT, \n'
 '\tprogress INTEGER, \n'
 '\tcurrent_step VARCHAR, \n'
 '\tlogs JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tcompleted_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_analysis_tasks_id ON analysis_tasks (id)',
 'CREATE INDEX ix_analysis_tasks_query ON analysis_tasks ("query")',
 'CREATE INDEX ix_analysis_tasks_target_brand ON analysis_tasks (target_brand)',
 'CREATE TABLE brain_messages (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\trole VARCHAR, \n'
 '\tcontent TEXT, \n'
 '\tthought_process TEXT, \n'
 '\tcitations JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES brain_sessions (id)\n'
 ')',
 'CREATE INDEX ix_brain_messages_id ON brain_messages (id)',
 'CREATE TABLE content_assets (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tcontent_body TEXT, \n'
 '\toriginal_input TEXT, \n'
 '\ttarget_platform VARCHAR, \n'
 '\tmeta_data JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_content_assets_id ON content_assets (id)',
 'CREATE TABLE digital_employees (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\trole VARCHAR(16), \n'
 '\tdescription TEXT, \n'
 '\tavatar_url VARCHAR, \n'
 '\tmodel_name VARCHAR, \n'
 '\tkb_search_behavior VARCHAR, \n'
 '\tsystem_prompt TEXT, \n'
 '\treasoning_config JSON, \n'
 '\tis_visible_on_landing BOOLEAN, \n'
 '\tcapabilities JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_digital_employees_id ON digital_employees (id)',
 'CREATE TABLE ecommerce_products (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tspu_code VARCHAR, \n'
 '\tsku_code VARCHAR, \n'
 '\tname VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tprice FLOAT, \n'
 '\tstock_quantity INTEGER, \n'
 '\tattributes JSON, \n'
 '\timages JSON, \n'
 '\tembedding_status VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_ecommerce_products_id ON ecommerce_products (id)',
 'CREATE INDEX ix_ecommerce_products_name ON ecommerce_products (name)',
 'CREATE UNIQUE INDEX ix_ecommerce_products_sku_code ON ecommerce_products (sku_code)',
 'CREATE INDEX ix_ecommerce_products_spu_code ON ecommerce_products (spu_code)',
 'CREATE TABLE inspection_records (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\ttotal_score FLOAT, \n'
 '\tstatus VARCHAR, \n'
 '\tissues JSON, \n'
 '\tsuggestion TEXT, \n'
 '\tmodel_used VARCHAR, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES brain_sessions (id)\n'
 ')',
 'CREATE INDEX ix_inspection_records_id ON inspection_records (id)',
 'CREATE TABLE knowledge_chunks (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tdoc_id INTEGER, \n'
 '\tchunk_text TEXT, \n'
 '\tchunk_index INTEGER, \n'
 '\tembedding VECTOR(1024), \n'
 '\tmeta_info JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(doc_id) REFERENCES knowledge_docs (id) ON DELETE CASCADE\n'
 ')',
 'CREATE INDEX idx_knowledge_chunks_embedding_hnsw ON knowledge_chunks (embedding)',
 'CREATE INDEX ix_knowledge_chunks_id ON knowledge_chunks (id)',
 'CREATE TABLE chat_sessions (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tsession_uuid VARCHAR, \n'
 '\tproject_id INTEGER, \n'
 '\temployee_id INTEGER, \n'
 '\tbot_id INTEGER, \n'
 '\tvisitor_id VARCHAR, \n'
 '\tuser_id INTEGER, \n'
 '\tvisitor_email VARCHAR, \n'
 '\tvisitor_name VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tsummary TEXT, \n'
 '\tintent JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_chat_sessions_bot_id ON chat_sessions (bot_id)',
 'CREATE INDEX ix_chat_sessions_id ON chat_sessions (id)',
 'CREATE UNIQUE INDEX ix_chat_sessions_session_uuid ON chat_sessions (session_uuid)',
 'CREATE INDEX ix_chat_sessions_visitor_id ON chat_sessions (visitor_id)',
 'CREATE TABLE employee_kbs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\temployee_id INTEGER, \n'
 '\tkb_id VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_employee_kbs_id ON employee_kbs (id)',
 'CREATE TABLE employee_skills (\n'
 '\tid INTEGER NOT NULL, \n'
 '\temployee_id INTEGER, \n'
 '\ttool_name VARCHAR, \n'
 '\tconfig JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_employee_skills_id ON employee_skills (id)',
 'CREATE TABLE missions (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tassigned_to INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tobjective TEXT, \n'
 '\tstatus VARCHAR(11), \n'
 '\tplan_summary TEXT, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(assigned_to) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_missions_id ON missions (id)',
 'CREATE TABLE rpa_jobs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tproject_id INTEGER, \n'
 '\tasset_id INTEGER, \n'
 '\tjob_type VARCHAR, \n'
 '\tplatform VARCHAR, \n'
 '\tpayload JSON, \n'
 '\tstatus VARCHAR, \n'
 '\tworker_id VARCHAR, \n'
 '\tretry_count INTEGER, \n'
 '\tresult_log TEXT, \n'
 '\texecution_logs JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(asset_id) REFERENCES content_assets (id)\n'
 ')',
 'CREATE INDEX ix_rpa_jobs_id ON rpa_jobs (id)',
 'CREATE TABLE chat_messages (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\trole VARCHAR, \n'
 '\tcontent TEXT, \n'
 '\tmeta_data JSON, \n'
 '\tcreated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES chat_sessions (id)\n'
 ')',
 'CREATE INDEX ix_chat_messages_id ON chat_messages (id)',
 'CREATE TABLE mission_tasks (\n'
 '\tid INTEGER NOT NULL, \n'
 '\tmission_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\ttask_type VARCHAR, \n'
 '\tstatus VARCHAR(9), \n'
 '\torder_index INTEGER, \n'
 '\tdependency_task_ids JSON, \n'
 '\tresult_data JSON, \n'
 '\terror_log TEXT, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(mission_id) REFERENCES missions (id)\n'
 ')',
 'CREATE INDEX ix_mission_tasks_id ON mission_tasks (id)')

PHASE1_SQLITE_DOWN = ('DROP INDEX IF EXISTS ix_mission_tasks_id',
 'DROP TABLE IF EXISTS mission_tasks',
 'DROP INDEX IF EXISTS ix_chat_messages_id',
 'DROP TABLE IF EXISTS chat_messages',
 'DROP INDEX IF EXISTS ix_rpa_jobs_id',
 'DROP TABLE IF EXISTS rpa_jobs',
 'DROP INDEX IF EXISTS ix_missions_id',
 'DROP TABLE IF EXISTS missions',
 'DROP INDEX IF EXISTS ix_employee_skills_id',
 'DROP TABLE IF EXISTS employee_skills',
 'DROP INDEX IF EXISTS ix_employee_kbs_id',
 'DROP TABLE IF EXISTS employee_kbs',
 'DROP INDEX IF EXISTS ix_chat_sessions_visitor_id',
 'DROP INDEX IF EXISTS ix_chat_sessions_session_uuid',
 'DROP INDEX IF EXISTS ix_chat_sessions_id',
 'DROP INDEX IF EXISTS ix_chat_sessions_bot_id',
 'DROP TABLE IF EXISTS chat_sessions',
 'DROP INDEX IF EXISTS ix_knowledge_chunks_id',
 'DROP INDEX IF EXISTS idx_knowledge_chunks_embedding_hnsw',
 'DROP TABLE IF EXISTS knowledge_chunks',
 'DROP INDEX IF EXISTS ix_inspection_records_id',
 'DROP TABLE IF EXISTS inspection_records',
 'DROP INDEX IF EXISTS ix_ecommerce_products_spu_code',
 'DROP INDEX IF EXISTS ix_ecommerce_products_sku_code',
 'DROP INDEX IF EXISTS ix_ecommerce_products_name',
 'DROP INDEX IF EXISTS ix_ecommerce_products_id',
 'DROP TABLE IF EXISTS ecommerce_products',
 'DROP INDEX IF EXISTS ix_digital_employees_id',
 'DROP TABLE IF EXISTS digital_employees',
 'DROP INDEX IF EXISTS ix_content_assets_id',
 'DROP TABLE IF EXISTS content_assets',
 'DROP INDEX IF EXISTS ix_brain_messages_id',
 'DROP TABLE IF EXISTS brain_messages',
 'DROP INDEX IF EXISTS ix_analysis_tasks_target_brand',
 'DROP INDEX IF EXISTS ix_analysis_tasks_query',
 'DROP INDEX IF EXISTS ix_analysis_tasks_id',
 'DROP TABLE IF EXISTS analysis_tasks',
 'DROP INDEX IF EXISTS ix_projects_name',
 'DROP INDEX IF EXISTS ix_projects_id',
 'DROP TABLE IF EXISTS projects',
 'DROP INDEX IF EXISTS ix_marketing_contents_user_id',
 'DROP INDEX IF EXISTS ix_marketing_contents_id',
 'DROP INDEX IF EXISTS ix_marketing_contents_content_type',
 'DROP TABLE IF EXISTS marketing_contents',
 'DROP INDEX IF EXISTS ix_llm_models_name',
 'DROP INDEX IF EXISTS ix_llm_models_id',
 'DROP TABLE IF EXISTS llm_models',
 'DROP INDEX IF EXISTS ix_knowledge_docs_id',
 'DROP TABLE IF EXISTS knowledge_docs',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_user_id',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_target_brand',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_id',
 'DROP TABLE IF EXISTS geo_watch_queries',
 'DROP INDEX IF EXISTS ix_brain_sessions_id',
 'DROP TABLE IF EXISTS brain_sessions',
 'DROP INDEX IF EXISTS ix_bots_name',
 'DROP INDEX IF EXISTS ix_bots_id',
 'DROP TABLE IF EXISTS bots',
 'DROP INDEX IF EXISTS ix_users_wechat_unionid',
 'DROP INDEX IF EXISTS ix_users_wechat_openid',
 'DROP INDEX IF EXISTS ix_users_username',
 'DROP INDEX IF EXISTS ix_users_id',
 'DROP INDEX IF EXISTS ix_users_email',
 'DROP TABLE IF EXISTS users',
 'DROP INDEX IF EXISTS ix_rag_configs_id',
 'DROP TABLE IF EXISTS rag_configs',
 'DROP INDEX IF EXISTS ix_quality_rules_name',
 'DROP INDEX IF EXISTS ix_quality_rules_id',
 'DROP TABLE IF EXISTS quality_rules',
 'DROP INDEX IF EXISTS ix_llm_providers_name',
 'DROP INDEX IF EXISTS ix_llm_providers_id',
 'DROP TABLE IF EXISTS llm_providers',
 'DROP INDEX IF EXISTS ix_leads_status',
 'DROP INDEX IF EXISTS ix_leads_source',
 'DROP INDEX IF EXISTS ix_leads_session_uuid',
 'DROP INDEX IF EXISTS ix_leads_organization_id',
 'DROP INDEX IF EXISTS ix_leads_id',
 'DROP INDEX IF EXISTS ix_leads_email',
 'DROP TABLE IF EXISTS leads',
 'DROP INDEX IF EXISTS ix_knowledge_bases_name',
 'DROP INDEX IF EXISTS ix_knowledge_bases_id',
 'DROP TABLE IF EXISTS knowledge_bases',
 'DROP INDEX IF EXISTS ix_organizations_name',
 'DROP INDEX IF EXISTS ix_organizations_invite_code',
 'DROP INDEX IF EXISTS ix_organizations_id',
 'DROP TABLE IF EXISTS organizations',
 'DROP INDEX IF EXISTS ix_llm_request_logs_user_id',
 'DROP INDEX IF EXISTS ix_llm_request_logs_trace_id',
 'DROP INDEX IF EXISTS ix_llm_request_logs_id',
 'DROP TABLE IF EXISTS llm_request_logs')

PHASE1_POSTGRES_UP = ("DO $$ BEGIN CREATE TYPE agentrole AS ENUM ('strategist', 'executor', 'archivist', 'customer_service'); EXCEPTION "
 'WHEN duplicate_object THEN NULL; END $$;',
 "DO $$ BEGIN CREATE TYPE missionstatus AS ENUM ('planning', 'in_progress', 'completed', 'failed'); EXCEPTION WHEN "
 'duplicate_object THEN NULL; END $$;',
 "DO $$ BEGIN CREATE TYPE taskstatus AS ENUM ('pending', 'running', 'completed', 'failed'); EXCEPTION WHEN "
 'duplicate_object THEN NULL; END $$;',
 'CREATE TABLE llm_request_logs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\ttrace_id VARCHAR, \n'
 '\tuser_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tmodel VARCHAR, \n'
 '\tinput_tokens INTEGER, \n'
 '\toutput_tokens INTEGER, \n'
 '\ttotal_tokens INTEGER, \n'
 '\tlatency_ms INTEGER, \n'
 '\tstatus VARCHAR, \n'
 '\terror_msg TEXT, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id)\n'
 ')',
 'CREATE INDEX ix_llm_request_logs_id ON llm_request_logs (id)',
 'CREATE INDEX ix_llm_request_logs_trace_id ON llm_request_logs (trace_id)',
 'CREATE INDEX ix_llm_request_logs_user_id ON llm_request_logs (user_id)',
 'CREATE TABLE organizations (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tinvite_code VARCHAR, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id)\n'
 ')',
 'CREATE INDEX ix_organizations_id ON organizations (id)',
 'CREATE UNIQUE INDEX ix_organizations_invite_code ON organizations (invite_code)',
 'CREATE UNIQUE INDEX ix_organizations_name ON organizations (name)',
 'CREATE TABLE knowledge_bases (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\tis_public BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_knowledge_bases_id ON knowledge_bases (id)',
 'CREATE INDEX ix_knowledge_bases_name ON knowledge_bases (name)',
 'CREATE TABLE leads (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tsource VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\temail VARCHAR, \n'
 '\tname VARCHAR, \n'
 '\tcompany VARCHAR, \n'
 '\tcountry VARCHAR, \n'
 '\tphone VARCHAR, \n'
 '\tproducts VARCHAR, \n'
 '\tintent_json JSON, \n'
 '\tconversation TEXT, \n'
 '\tsession_uuid VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_leads_email ON leads (email)',
 'CREATE INDEX ix_leads_id ON leads (id)',
 'CREATE INDEX ix_leads_organization_id ON leads (organization_id)',
 'CREATE INDEX ix_leads_session_uuid ON leads (session_uuid)',
 'CREATE INDEX ix_leads_source ON leads (source)',
 'CREATE INDEX ix_leads_status ON leads (status)',
 'CREATE TABLE llm_providers (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tbase_url VARCHAR, \n'
 '\tapi_key VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_llm_providers_id ON llm_providers (id)',
 'CREATE INDEX ix_llm_providers_name ON llm_providers (name)',
 'CREATE TABLE quality_rules (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tweight FLOAT, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_quality_rules_id ON quality_rules (id)',
 'CREATE INDEX ix_quality_rules_name ON quality_rules (name)',
 'CREATE TABLE rag_configs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\ttop_k INTEGER, \n'
 '\tscore_threshold FLOAT, \n'
 '\tchunk_size INTEGER, \n'
 '\tchunk_overlap INTEGER, \n'
 '\tsensitive_words TEXT, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_rag_configs_id ON rag_configs (id)',
 'CREATE TABLE users (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tusername VARCHAR, \n'
 '\tnickname VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\temail VARCHAR, \n'
 '\thashed_password VARCHAR, \n'
 '\twechat_openid VARCHAR, \n'
 '\twechat_unionid VARCHAR, \n'
 '\tphone VARCHAR, \n'
 '\tbio TEXT, \n'
 '\trole VARCHAR, \n'
 '\torganization_id INTEGER, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE UNIQUE INDEX ix_users_email ON users (email)',
 'CREATE INDEX ix_users_id ON users (id)',
 'CREATE UNIQUE INDEX ix_users_username ON users (username)',
 'CREATE UNIQUE INDEX ix_users_wechat_openid ON users (wechat_openid)',
 'CREATE UNIQUE INDEX ix_users_wechat_unionid ON users (wechat_unionid)',
 'CREATE TABLE bots (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tavatar VARCHAR, \n'
 '\tsystem_prompt TEXT, \n'
 '\twelcome_message VARCHAR, \n'
 '\tmodel_name VARCHAR, \n'
 '\ttemperature FLOAT, \n'
 '\tkb_id INTEGER, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(kb_id) REFERENCES knowledge_bases (id)\n'
 ')',
 'CREATE INDEX ix_bots_id ON bots (id)',
 'CREATE INDEX ix_bots_name ON bots (name)',
 'CREATE TABLE brain_sessions (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\torganization_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id)\n'
 ')',
 'CREATE INDEX ix_brain_sessions_id ON brain_sessions (id)',
 'CREATE TABLE geo_watch_queries (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\ttarget_brand VARCHAR NOT NULL, \n'
 '\tquery VARCHAR NOT NULL, \n'
 '\tengine_name VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tinterval_hours INTEGER, \n'
 '\tenabled BOOLEAN, \n'
 '\tlast_run_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tnext_run_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tlast_task_id INTEGER, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_geo_watch_queries_id ON geo_watch_queries (id)',
 'CREATE INDEX ix_geo_watch_queries_target_brand ON geo_watch_queries (target_brand)',
 'CREATE INDEX ix_geo_watch_queries_user_id ON geo_watch_queries (user_id)',
 'CREATE TABLE knowledge_docs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tkb_id INTEGER, \n'
 '\tfilename VARCHAR, \n'
 '\tfile_path VARCHAR, \n'
 '\tfile_type VARCHAR, \n'
 '\tfile_size INTEGER, \n'
 '\tstatus VARCHAR, \n'
 '\terror_msg TEXT, \n'
 '\tchunk_count INTEGER, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(kb_id) REFERENCES knowledge_bases (id)\n'
 ')',
 'CREATE INDEX ix_knowledge_docs_id ON knowledge_docs (id)',
 'CREATE TABLE llm_models (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tprovider_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdisplay_name VARCHAR, \n'
 '\ttype VARCHAR, \n'
 '\tcontext_window VARCHAR, \n'
 '\tis_active BOOLEAN, \n'
 '\tsupports_geo BOOLEAN, \n'
 '\tsupports_chat BOOLEAN, \n'
 '\tapi_key VARCHAR, \n'
 '\tbase_url VARCHAR, \n'
 '\tis_default BOOLEAN, \n'
 '\tis_kb_search_default BOOLEAN, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(provider_id) REFERENCES llm_providers (id)\n'
 ')',
 'CREATE INDEX ix_llm_models_id ON llm_models (id)',
 'CREATE UNIQUE INDEX ix_llm_models_name ON llm_models (name)',
 'CREATE TABLE marketing_contents (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tcontent_type VARCHAR, \n'
 '\tproduct_name VARCHAR, \n'
 '\tselling_points TEXT, \n'
 '\tlanguage VARCHAR, \n'
 '\ttitle VARCHAR, \n'
 '\tbody TEXT, \n'
 '\ttags JSON, \n'
 '\timage_url VARCHAR, \n'
 '\tprompt TEXT, \n'
 '\textra JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_marketing_contents_content_type ON marketing_contents (content_type)',
 'CREATE INDEX ix_marketing_contents_id ON marketing_contents (id)',
 'CREATE INDEX ix_marketing_contents_user_id ON marketing_contents (user_id)',
 'CREATE TABLE projects (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\tdomain VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tcompetitors JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_projects_id ON projects (id)',
 'CREATE INDEX ix_projects_name ON projects (name)',
 'CREATE TABLE analysis_tasks (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\ttarget_brand VARCHAR, \n'
 '\tquery VARCHAR, \n'
 '\tengine_name VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tis_mentioned BOOLEAN, \n'
 '\trank_position INTEGER, \n'
 '\tsentiment_score FLOAT, \n'
 '\treasoning TEXT, \n'
 '\tcitations JSON, \n'
 '\tsuggestions JSON, \n'
 '\traw_response TEXT, \n'
 '\tprogress INTEGER, \n'
 '\tcurrent_step VARCHAR, \n'
 '\tlogs JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tcompleted_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_analysis_tasks_id ON analysis_tasks (id)',
 'CREATE INDEX ix_analysis_tasks_query ON analysis_tasks (query)',
 'CREATE INDEX ix_analysis_tasks_target_brand ON analysis_tasks (target_brand)',
 'CREATE TABLE brain_messages (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\trole VARCHAR, \n'
 '\tcontent TEXT, \n'
 '\tthought_process TEXT, \n'
 '\tcitations JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES brain_sessions (id)\n'
 ')',
 'CREATE INDEX ix_brain_messages_id ON brain_messages (id)',
 'CREATE TABLE content_assets (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tcontent_body TEXT, \n'
 '\toriginal_input TEXT, \n'
 '\ttarget_platform VARCHAR, \n'
 '\tmeta_data JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_content_assets_id ON content_assets (id)',
 'CREATE TABLE digital_employees (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tname VARCHAR, \n'
 '\trole agentrole, \n'
 '\tdescription TEXT, \n'
 '\tavatar_url VARCHAR, \n'
 '\tmodel_name VARCHAR, \n'
 '\tkb_search_behavior VARCHAR, \n'
 '\tsystem_prompt TEXT, \n'
 '\treasoning_config JSON, \n'
 '\tis_visible_on_landing BOOLEAN, \n'
 '\tcapabilities JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_digital_employees_id ON digital_employees (id)',
 'CREATE TABLE ecommerce_products (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tspu_code VARCHAR, \n'
 '\tsku_code VARCHAR, \n'
 '\tname VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\tprice FLOAT, \n'
 '\tstock_quantity INTEGER, \n'
 '\tattributes JSON, \n'
 '\timages JSON, \n'
 '\tembedding_status VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id)\n'
 ')',
 'CREATE INDEX ix_ecommerce_products_id ON ecommerce_products (id)',
 'CREATE INDEX ix_ecommerce_products_name ON ecommerce_products (name)',
 'CREATE UNIQUE INDEX ix_ecommerce_products_sku_code ON ecommerce_products (sku_code)',
 'CREATE INDEX ix_ecommerce_products_spu_code ON ecommerce_products (spu_code)',
 'CREATE TABLE inspection_records (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\ttotal_score FLOAT, \n'
 '\tstatus VARCHAR, \n'
 '\tissues JSON, \n'
 '\tsuggestion TEXT, \n'
 '\tmodel_used VARCHAR, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES brain_sessions (id)\n'
 ')',
 'CREATE INDEX ix_inspection_records_id ON inspection_records (id)',
 'CREATE TABLE knowledge_chunks (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tdoc_id INTEGER, \n'
 '\tchunk_text TEXT, \n'
 '\tchunk_index INTEGER, \n'
 '\tembedding VECTOR(1024), \n'
 '\tmeta_info JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(doc_id) REFERENCES knowledge_docs (id) ON DELETE CASCADE\n'
 ')',
 'CREATE INDEX idx_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops) WITH '
 '(m = 16, ef_construction = 64)',
 'CREATE INDEX ix_knowledge_chunks_id ON knowledge_chunks (id)',
 'CREATE TABLE chat_sessions (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tsession_uuid VARCHAR, \n'
 '\tproject_id INTEGER, \n'
 '\temployee_id INTEGER, \n'
 '\tbot_id INTEGER, \n'
 '\tvisitor_id VARCHAR, \n'
 '\tuser_id INTEGER, \n'
 '\tvisitor_email VARCHAR, \n'
 '\tvisitor_name VARCHAR, \n'
 '\tlanguage VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tsummary TEXT, \n'
 '\tintent JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id)\n'
 ')',
 'CREATE INDEX ix_chat_sessions_bot_id ON chat_sessions (bot_id)',
 'CREATE INDEX ix_chat_sessions_id ON chat_sessions (id)',
 'CREATE UNIQUE INDEX ix_chat_sessions_session_uuid ON chat_sessions (session_uuid)',
 'CREATE INDEX ix_chat_sessions_visitor_id ON chat_sessions (visitor_id)',
 'CREATE TABLE employee_kbs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\temployee_id INTEGER, \n'
 '\tkb_id VARCHAR, \n'
 '\tdescription VARCHAR, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_employee_kbs_id ON employee_kbs (id)',
 'CREATE TABLE employee_skills (\n'
 '\tid SERIAL NOT NULL, \n'
 '\temployee_id INTEGER, \n'
 '\ttool_name VARCHAR, \n'
 '\tconfig JSON, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(employee_id) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_employee_skills_id ON employee_skills (id)',
 'CREATE TABLE missions (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tproject_id INTEGER, \n'
 '\tassigned_to INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tobjective TEXT, \n'
 '\tstatus missionstatus, \n'
 '\tplan_summary TEXT, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(assigned_to) REFERENCES digital_employees (id)\n'
 ')',
 'CREATE INDEX ix_missions_id ON missions (id)',
 'CREATE TABLE rpa_jobs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tuser_id INTEGER, \n'
 '\tproject_id INTEGER, \n'
 '\tasset_id INTEGER, \n'
 '\tjob_type VARCHAR, \n'
 '\tplatform VARCHAR, \n'
 '\tpayload JSON, \n'
 '\tstatus VARCHAR, \n'
 '\tworker_id VARCHAR, \n'
 '\tretry_count INTEGER, \n'
 '\tresult_log TEXT, \n'
 '\texecution_logs JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(user_id) REFERENCES users (id), \n'
 '\tFOREIGN KEY(project_id) REFERENCES projects (id), \n'
 '\tFOREIGN KEY(asset_id) REFERENCES content_assets (id)\n'
 ')',
 'CREATE INDEX ix_rpa_jobs_id ON rpa_jobs (id)',
 'CREATE TABLE chat_messages (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tsession_id INTEGER, \n'
 '\trole VARCHAR, \n'
 '\tcontent TEXT, \n'
 '\tmeta_data JSON, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(session_id) REFERENCES chat_sessions (id)\n'
 ')',
 'CREATE INDEX ix_chat_messages_id ON chat_messages (id)',
 'CREATE TABLE mission_tasks (\n'
 '\tid SERIAL NOT NULL, \n'
 '\tmission_id INTEGER, \n'
 '\ttitle VARCHAR, \n'
 '\tdescription TEXT, \n'
 '\ttask_type VARCHAR, \n'
 '\tstatus taskstatus, \n'
 '\torder_index INTEGER, \n'
 '\tdependency_task_ids JSON, \n'
 '\tresult_data JSON, \n'
 '\terror_log TEXT, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(mission_id) REFERENCES missions (id)\n'
 ')',
 'CREATE INDEX ix_mission_tasks_id ON mission_tasks (id)')

PHASE1_POSTGRES_DOWN = ('DROP INDEX IF EXISTS ix_mission_tasks_id',
 'DROP TABLE IF EXISTS mission_tasks',
 'DROP INDEX IF EXISTS ix_chat_messages_id',
 'DROP TABLE IF EXISTS chat_messages',
 'DROP INDEX IF EXISTS ix_rpa_jobs_id',
 'DROP TABLE IF EXISTS rpa_jobs',
 'DROP INDEX IF EXISTS ix_missions_id',
 'DROP TABLE IF EXISTS missions',
 'DROP INDEX IF EXISTS ix_employee_skills_id',
 'DROP TABLE IF EXISTS employee_skills',
 'DROP INDEX IF EXISTS ix_employee_kbs_id',
 'DROP TABLE IF EXISTS employee_kbs',
 'DROP INDEX IF EXISTS ix_chat_sessions_visitor_id',
 'DROP INDEX IF EXISTS ix_chat_sessions_session_uuid',
 'DROP INDEX IF EXISTS ix_chat_sessions_id',
 'DROP INDEX IF EXISTS ix_chat_sessions_bot_id',
 'DROP TABLE IF EXISTS chat_sessions',
 'DROP INDEX IF EXISTS ix_knowledge_chunks_id',
 'DROP INDEX IF EXISTS idx_knowledge_chunks_embedding_hnsw',
 'DROP TABLE IF EXISTS knowledge_chunks',
 'DROP INDEX IF EXISTS ix_inspection_records_id',
 'DROP TABLE IF EXISTS inspection_records',
 'DROP INDEX IF EXISTS ix_ecommerce_products_spu_code',
 'DROP INDEX IF EXISTS ix_ecommerce_products_sku_code',
 'DROP INDEX IF EXISTS ix_ecommerce_products_name',
 'DROP INDEX IF EXISTS ix_ecommerce_products_id',
 'DROP TABLE IF EXISTS ecommerce_products',
 'DROP INDEX IF EXISTS ix_digital_employees_id',
 'DROP TABLE IF EXISTS digital_employees',
 'DROP INDEX IF EXISTS ix_content_assets_id',
 'DROP TABLE IF EXISTS content_assets',
 'DROP INDEX IF EXISTS ix_brain_messages_id',
 'DROP TABLE IF EXISTS brain_messages',
 'DROP INDEX IF EXISTS ix_analysis_tasks_target_brand',
 'DROP INDEX IF EXISTS ix_analysis_tasks_query',
 'DROP INDEX IF EXISTS ix_analysis_tasks_id',
 'DROP TABLE IF EXISTS analysis_tasks',
 'DROP INDEX IF EXISTS ix_projects_name',
 'DROP INDEX IF EXISTS ix_projects_id',
 'DROP TABLE IF EXISTS projects',
 'DROP INDEX IF EXISTS ix_marketing_contents_user_id',
 'DROP INDEX IF EXISTS ix_marketing_contents_id',
 'DROP INDEX IF EXISTS ix_marketing_contents_content_type',
 'DROP TABLE IF EXISTS marketing_contents',
 'DROP INDEX IF EXISTS ix_llm_models_name',
 'DROP INDEX IF EXISTS ix_llm_models_id',
 'DROP TABLE IF EXISTS llm_models',
 'DROP INDEX IF EXISTS ix_knowledge_docs_id',
 'DROP TABLE IF EXISTS knowledge_docs',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_user_id',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_target_brand',
 'DROP INDEX IF EXISTS ix_geo_watch_queries_id',
 'DROP TABLE IF EXISTS geo_watch_queries',
 'DROP INDEX IF EXISTS ix_brain_sessions_id',
 'DROP TABLE IF EXISTS brain_sessions',
 'DROP INDEX IF EXISTS ix_bots_name',
 'DROP INDEX IF EXISTS ix_bots_id',
 'DROP TABLE IF EXISTS bots',
 'DROP INDEX IF EXISTS ix_users_wechat_unionid',
 'DROP INDEX IF EXISTS ix_users_wechat_openid',
 'DROP INDEX IF EXISTS ix_users_username',
 'DROP INDEX IF EXISTS ix_users_id',
 'DROP INDEX IF EXISTS ix_users_email',
 'DROP TABLE IF EXISTS users',
 'DROP INDEX IF EXISTS ix_rag_configs_id',
 'DROP TABLE IF EXISTS rag_configs',
 'DROP INDEX IF EXISTS ix_quality_rules_name',
 'DROP INDEX IF EXISTS ix_quality_rules_id',
 'DROP TABLE IF EXISTS quality_rules',
 'DROP INDEX IF EXISTS ix_llm_providers_name',
 'DROP INDEX IF EXISTS ix_llm_providers_id',
 'DROP TABLE IF EXISTS llm_providers',
 'DROP INDEX IF EXISTS ix_leads_status',
 'DROP INDEX IF EXISTS ix_leads_source',
 'DROP INDEX IF EXISTS ix_leads_session_uuid',
 'DROP INDEX IF EXISTS ix_leads_organization_id',
 'DROP INDEX IF EXISTS ix_leads_id',
 'DROP INDEX IF EXISTS ix_leads_email',
 'DROP TABLE IF EXISTS leads',
 'DROP INDEX IF EXISTS ix_knowledge_bases_name',
 'DROP INDEX IF EXISTS ix_knowledge_bases_id',
 'DROP TABLE IF EXISTS knowledge_bases',
 'DROP INDEX IF EXISTS ix_organizations_name',
 'DROP INDEX IF EXISTS ix_organizations_invite_code',
 'DROP INDEX IF EXISTS ix_organizations_id',
 'DROP TABLE IF EXISTS organizations',
 'DROP INDEX IF EXISTS ix_llm_request_logs_user_id',
 'DROP INDEX IF EXISTS ix_llm_request_logs_trace_id',
 'DROP INDEX IF EXISTS ix_llm_request_logs_id',
 'DROP TABLE IF EXISTS llm_request_logs',
 'DROP TYPE IF EXISTS taskstatus',
 'DROP TYPE IF EXISTS missionstatus',
 'DROP TYPE IF EXISTS agentrole')

PHASE2_HELPERS_SQLITE_UP = ('CREATE TABLE crm_entity_links (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tlead_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tproject_id VARCHAR, \n'
 '\tremote_customer_id VARCHAR, \n'
 '\tremote_status VARCHAR, \n'
 '\tremote_updated_at DATETIME, \n'
 '\tsynced_at DATETIME, \n'
 '\tarchived_at DATETIME, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_entity_links_id ON crm_entity_links (id)',
 'CREATE INDEX ix_crm_entity_links_lead_id ON crm_entity_links (lead_id)',
 'CREATE INDEX ix_crm_entity_links_organization_id ON crm_entity_links (organization_id)',
 'CREATE UNIQUE INDEX uq_crm_link_org_lead_project ON crm_entity_links (provider, organization_id, lead_id, '
 'project_id)',
 'CREATE UNIQUE INDEX uq_crm_link_remote ON crm_entity_links (provider, project_id, remote_customer_id)',
 'CREATE TABLE crm_outcome_events (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tevent_id VARCHAR, \n'
 '\tremote_customer_id VARCHAR, \n'
 '\texternal_id VARCHAR, \n'
 '\tlead_id INTEGER, \n'
 '\tfrom_status VARCHAR, \n'
 '\tto_status VARCHAR, \n'
 '\toccurred_at DATETIME, \n'
 '\tprocessed_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_outcome_events_id ON crm_outcome_events (id)',
 'CREATE INDEX ix_crm_outcome_events_organization_id ON crm_outcome_events (organization_id)',
 'CREATE UNIQUE INDEX uq_crm_outcome_event ON crm_outcome_events (provider, organization_id, event_id)',
 'CREATE TABLE crm_sync_jobs (\n'
 '\tid INTEGER NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tlead_id INTEGER, \n'
 '\tproject_id VARCHAR, \n'
 '\tevent_type VARCHAR, \n'
 '\tidempotency_key VARCHAR, \n'
 '\tpayload_version VARCHAR, \n'
 '\tpayload_json JSON, \n'
 '\tpayload_hash VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tattempt_count INTEGER, \n'
 '\tnext_attempt_at DATETIME, \n'
 '\tlease_owner VARCHAR, \n'
 '\tlease_expires_at DATETIME, \n'
 '\tlast_error_code VARCHAR, \n'
 '\tlast_error_summary TEXT, \n'
 '\tlast_http_status INTEGER, \n'
 '\tcreated_at DATETIME, \n'
 '\tupdated_at DATETIME, \n'
 '\tsucceeded_at DATETIME, \n'
 '\tdead_at DATETIME, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_sync_jobs_id ON crm_sync_jobs (id)',
 'CREATE UNIQUE INDEX ix_crm_sync_jobs_idempotency_key ON crm_sync_jobs (idempotency_key)',
 'CREATE INDEX ix_crm_sync_jobs_lead_id ON crm_sync_jobs (lead_id)',
 'CREATE INDEX ix_crm_sync_jobs_next_attempt_at ON crm_sync_jobs (next_attempt_at)',
 'CREATE INDEX ix_crm_sync_jobs_organization_id ON crm_sync_jobs (organization_id)',
 'CREATE INDEX ix_crm_sync_jobs_project_id ON crm_sync_jobs (project_id)',
 'CREATE INDEX ix_crm_sync_jobs_status ON crm_sync_jobs (status)')

PHASE2_HELPERS_SQLITE_DOWN = ('DROP INDEX IF EXISTS ix_crm_sync_jobs_status',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_project_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_organization_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_next_attempt_at',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_lead_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_idempotency_key',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_id',
 'DROP TABLE IF EXISTS crm_sync_jobs',
 'DROP INDEX IF EXISTS uq_crm_outcome_event',
 'DROP INDEX IF EXISTS ix_crm_outcome_events_organization_id',
 'DROP INDEX IF EXISTS ix_crm_outcome_events_id',
 'DROP TABLE IF EXISTS crm_outcome_events',
 'DROP INDEX IF EXISTS uq_crm_link_remote',
 'DROP INDEX IF EXISTS uq_crm_link_org_lead_project',
 'DROP INDEX IF EXISTS ix_crm_entity_links_organization_id',
 'DROP INDEX IF EXISTS ix_crm_entity_links_lead_id',
 'DROP INDEX IF EXISTS ix_crm_entity_links_id',
 'DROP TABLE IF EXISTS crm_entity_links')
PHASE2_HELPERS_POSTGRES_UP = ('CREATE TABLE crm_entity_links (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tlead_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tproject_id VARCHAR, \n'
 '\tremote_customer_id VARCHAR, \n'
 '\tremote_status VARCHAR, \n'
 '\tremote_updated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tsynced_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tarchived_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_entity_links_id ON crm_entity_links (id)',
 'CREATE INDEX ix_crm_entity_links_lead_id ON crm_entity_links (lead_id)',
 'CREATE INDEX ix_crm_entity_links_organization_id ON crm_entity_links (organization_id)',
 'CREATE UNIQUE INDEX uq_crm_link_org_lead_project ON crm_entity_links (provider, organization_id, lead_id, '
 'project_id)',
 'CREATE UNIQUE INDEX uq_crm_link_remote ON crm_entity_links (provider, project_id, remote_customer_id)',
 'CREATE TABLE crm_outcome_events (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tprovider VARCHAR, \n'
 '\tevent_id VARCHAR, \n'
 '\tremote_customer_id VARCHAR, \n'
 '\texternal_id VARCHAR, \n'
 '\tlead_id INTEGER, \n'
 '\tfrom_status VARCHAR, \n'
 '\tto_status VARCHAR, \n'
 '\toccurred_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tprocessed_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_outcome_events_id ON crm_outcome_events (id)',
 'CREATE INDEX ix_crm_outcome_events_organization_id ON crm_outcome_events (organization_id)',
 'CREATE UNIQUE INDEX uq_crm_outcome_event ON crm_outcome_events (provider, organization_id, event_id)',
 'CREATE TABLE crm_sync_jobs (\n'
 '\tid SERIAL NOT NULL, \n'
 '\torganization_id INTEGER, \n'
 '\tlead_id INTEGER, \n'
 '\tproject_id VARCHAR, \n'
 '\tevent_type VARCHAR, \n'
 '\tidempotency_key VARCHAR, \n'
 '\tpayload_version VARCHAR, \n'
 '\tpayload_json JSON, \n'
 '\tpayload_hash VARCHAR, \n'
 '\tstatus VARCHAR, \n'
 '\tattempt_count INTEGER, \n'
 '\tnext_attempt_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tlease_owner VARCHAR, \n'
 '\tlease_expires_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tlast_error_code VARCHAR, \n'
 '\tlast_error_summary TEXT, \n'
 '\tlast_http_status INTEGER, \n'
 '\tcreated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tupdated_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tsucceeded_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tdead_at TIMESTAMP WITHOUT TIME ZONE, \n'
 '\tPRIMARY KEY (id), \n'
 '\tFOREIGN KEY(organization_id) REFERENCES organizations (id), \n'
 '\tFOREIGN KEY(lead_id) REFERENCES leads (id)\n'
 ')',
 'CREATE INDEX ix_crm_sync_jobs_id ON crm_sync_jobs (id)',
 'CREATE UNIQUE INDEX ix_crm_sync_jobs_idempotency_key ON crm_sync_jobs (idempotency_key)',
 'CREATE INDEX ix_crm_sync_jobs_lead_id ON crm_sync_jobs (lead_id)',
 'CREATE INDEX ix_crm_sync_jobs_next_attempt_at ON crm_sync_jobs (next_attempt_at)',
 'CREATE INDEX ix_crm_sync_jobs_organization_id ON crm_sync_jobs (organization_id)',
 'CREATE INDEX ix_crm_sync_jobs_project_id ON crm_sync_jobs (project_id)',
 'CREATE INDEX ix_crm_sync_jobs_status ON crm_sync_jobs (status)')

PHASE2_HELPERS_POSTGRES_DOWN = ('DROP INDEX IF EXISTS ix_crm_sync_jobs_status',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_project_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_organization_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_next_attempt_at',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_lead_id',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_idempotency_key',
 'DROP INDEX IF EXISTS ix_crm_sync_jobs_id',
 'DROP TABLE IF EXISTS crm_sync_jobs',
 'DROP INDEX IF EXISTS uq_crm_outcome_event',
 'DROP INDEX IF EXISTS ix_crm_outcome_events_organization_id',
 'DROP INDEX IF EXISTS ix_crm_outcome_events_id',
 'DROP TABLE IF EXISTS crm_outcome_events',
 'DROP INDEX IF EXISTS uq_crm_link_remote',
 'DROP INDEX IF EXISTS uq_crm_link_org_lead_project',
 'DROP INDEX IF EXISTS ix_crm_entity_links_organization_id',
 'DROP INDEX IF EXISTS ix_crm_entity_links_lead_id',
 'DROP INDEX IF EXISTS ix_crm_entity_links_id',
 'DROP TABLE IF EXISTS crm_entity_links')
