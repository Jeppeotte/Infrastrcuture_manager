SELECT 
  d1.time,
  CASE 
    WHEN (SELECT d2.state 
          FROM device_states d2
          WHERE d2.node_id = 'AAUGATEWAY'
            AND d2.device_id = 'SiemensPLC'
            AND d2.message_type = 'STATE'
            AND d2.state_key = 'process_trigger'
            AND d2.time <= d1.time
            AND d2.state IS NOT NULL
          ORDER BY d2.time DESC
          LIMIT 1) = 'True' THEN 'Running'
    WHEN (SELECT d2.state 
          FROM device_states d2
          WHERE d2.node_id = 'AAUGATEWAY'
            AND d2.device_id = 'SiemensPLC'
            AND d2.message_type = 'STATE'
            AND d2.state_key = 'process_trigger'
            AND d2.time <= d1.time
            AND d2.state IS NOT NULL
          ORDER BY d2.time DESC
          LIMIT 1) = 'False' THEN 'Idle'
    ELSE NULL
  END AS process_trigger,
  
  CASE 
    WHEN (SELECT d3.state
          FROM device_states d3
          WHERE d3.node_id = 'AAUGATEWAY'
            AND d3.device_id = 'SiemensPLC'
            AND d3.message_type = 'STATE'
            AND d3.state_key = 'data_trigger'
            AND d3.time <= d1.time
            AND d3.state IS NOT NULL
          ORDER BY d3.time DESC
          LIMIT 1) = 'True' THEN 'Sampling'
    WHEN (SELECT d3.state
          FROM device_states d3
          WHERE d3.node_id = 'AAUGATEWAY'
            AND d3.device_id = 'SiemensPLC'
            AND d3.message_type = 'STATE'
            AND d3.state_key = 'data_trigger'
            AND d3.time <= d1.time
            AND d3.state IS NOT NULL
          ORDER BY d3.time DESC
          LIMIT 1) = 'False' THEN 'Waiting'
    ELSE NULL
  END AS data_trigger
FROM 
  (SELECT DISTINCT time FROM device_states
   WHERE node_id = 'AAUGATEWAY'
     AND device_id = 'SiemensPLC'
     AND message_type = 'STATE') d1
ORDER BY d1.time;
