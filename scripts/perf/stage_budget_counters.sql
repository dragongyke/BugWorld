SELECT t.name, coalesce(p.name,tp.name,'runtime/global') AS process,
  COUNT(*) AS samples, ROUND(AVG(c.value),3) AS average,
  MIN(c.value) AS minimum, MAX(c.value) AS maximum
FROM counter c
JOIN counter_track t ON c.track_id=t.id
LEFT JOIN process_counter_track pt ON pt.id=t.id
LEFT JOIN process p ON p.upid=pt.upid
LEFT JOIN thread_counter_track tt ON tt.id=t.id
LEFT JOIN thread th ON th.utid=tt.utid
LEFT JOIN process tp ON tp.upid=th.upid
WHERE t.name IN (
  'Draw Call Count','Shadow Draw Call Count','Shadow Triangle Count',
  '3D Mesh Draw Call Count','3D Mesh Triangle Count','frameRate','RenderRate',
  'gpufreq','Texture2D Memory','Skeletal Animation Count'
) OR t.name GLOB 'frameRate_*'
GROUP BY t.id ORDER BY t.name;
