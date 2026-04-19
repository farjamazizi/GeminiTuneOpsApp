from kfp import dsl
from kfp import compiler

@dsl.component(
    base_image='python:3.11',
    packages_to_install=['google-cloud-storage>=2.19.0'],
)
def stage_dataset_for_tuning(source_gcs_uri:str, pipeline_root:str, model_display_name:str, dataset_split:str) -> str:
    from google.cloud import storage

    def split_gcs_uri(gcs_uri: str) -> tuple[str, str]:
        if not gcs_uri.startswith('gs://'):
            raise ValueError(f'Expected gs:// URI, got: {gcs_uri}')
        bucket_and_path = gcs_uri.removeprefix('gs://')
        bucket_name, _, blob_name = bucket_and_path.partition('/')
        if not bucket_name or not blob_name:
            raise ValueError(f'Incomplete GCS URI: {gcs_uri}')
        return bucket_name, blob_name

    destination_bucket_name, root_prefix = split_gcs_uri(pipeline_root)
    source_bucket_name, source_blob_name = split_gcs_uri(source_gcs_uri)
    root_prefix = root_prefix.rstrip('/')
    destination_blob_name = '/'.join(
        part
        for part in [root_prefix, 'staged-datasets', model_display_name, f'{dataset_split}.jsonl']
        if part
    )

    storage_client = storage.Client()
    source_bucket = storage_client.bucket(source_bucket_name)
    destination_bucket = storage_client.bucket(destination_bucket_name)
    source_blob = source_bucket.blob(source_blob_name)
    destination_blob = destination_bucket.blob(destination_blob_name)

    print(f'Preparing to stage dataset_split={dataset_split}')
    print(f'Source URI: {source_gcs_uri}')
    print(f'Destination URI: gs://{destination_bucket_name}/{destination_blob_name}')

    if not source_blob.exists(storage_client):
        raise FileNotFoundError(f'Source dataset does not exist: {source_gcs_uri}')

    destination_bucket.reload(client=storage_client)
    print(f'Destination bucket confirmed: {destination_bucket.name}')

    rewrite_token = None
    while True:
        rewrite_token, bytes_rewritten, total_bytes = destination_blob.rewrite(
            source=source_blob,
            token=rewrite_token,
            client=storage_client,
        )
        print(f'Rewrite progress: {bytes_rewritten}/{total_bytes} bytes')
        if not rewrite_token:
            break

    staged_uri = f'gs://{destination_bucket_name}/{destination_blob_name}'
    print(f'Staged {source_gcs_uri} to {staged_uri}')
    return staged_uri

@dsl.component(
    base_image='python:3.11',
    packages_to_install=['google-cloud-aiplatform>=1.111.0'],
)
def start_gemini_tuning(project_id:str, region:str, model_display_name:str, source_model:str, train_dataset_gcs_uri:str, evaluation_dataset_gcs_uri:str, pipeline_root:str) -> str:
    import vertexai
    from vertexai.tuning import sft
    vertexai.init(project=project_id, location=region)
    output_uri = f"{pipeline_root.rstrip('/')}/tuning-artifacts/{model_display_name}"
    tuning_job = sft.train(source_model=source_model, train_dataset=train_dataset_gcs_uri, validation_dataset=evaluation_dataset_gcs_uri, tuned_model_display_name=model_display_name, output_uri=output_uri)
    print(tuning_job.resource_name)
    return tuning_job.resource_name

@dsl.component(
    base_image='python:3.11',
    packages_to_install=['google-cloud-aiplatform>=1.111.0'],
)
def wait_for_gemini_tuning(project_id:str, region:str, tuning_job_name:str, poll_interval_seconds:int=60) -> str:
    import time
    import vertexai
    from vertexai.tuning import sft
    vertexai.init(project=project_id, location=region)
    tuning_job = sft.SupervisedTuningJob(tuning_job_name=tuning_job_name)
    while True:
        tuning_job.refresh()
        state_name = getattr(tuning_job.state, 'name', str(tuning_job.state))
        print(f'Tuning job {tuning_job_name} state: {state_name}')
        if tuning_job.has_ended:
            break
        time.sleep(max(poll_interval_seconds, 30))
    if state_name != 'JOB_STATE_SUCCEEDED':
        raise RuntimeError(f'Tuning job {tuning_job_name} ended with state {state_name}')
    tuned_model_name = tuning_job.tuned_model_name or ''
    print(f'Tuned model: {tuned_model_name}')
    return tuned_model_name

@dsl.pipeline(name='gemini-tuning-pipeline')
def gemini_tuning_pipeline(project_id:str, region:str, model_display_name:str, source_model:str, pipeline_root:str, training_source_gcs_uri:str, evaluation_source_gcs_uri:str, poll_interval_seconds:int=60):
    train_stage_task = stage_dataset_for_tuning(source_gcs_uri=training_source_gcs_uri, pipeline_root=pipeline_root, model_display_name=model_display_name, dataset_split='training')
    train_stage_task.set_caching_options(False)
    train_stage_task.set_cpu_limit('1')
    train_stage_task.set_memory_limit('4Gi')

    eval_stage_task = stage_dataset_for_tuning(source_gcs_uri=evaluation_source_gcs_uri, pipeline_root=pipeline_root, model_display_name=model_display_name, dataset_split='validation')
    eval_stage_task.after(train_stage_task)
    eval_stage_task.set_caching_options(False)
    eval_stage_task.set_cpu_limit('1')
    eval_stage_task.set_memory_limit('4Gi')

    start_tuning_task = start_gemini_tuning(project_id=project_id, region=region, model_display_name=model_display_name, source_model=source_model, train_dataset_gcs_uri=train_stage_task.output, evaluation_dataset_gcs_uri=eval_stage_task.output, pipeline_root=pipeline_root)
    start_tuning_task.set_caching_options(False)
    start_tuning_task.set_cpu_limit('1')
    start_tuning_task.set_memory_limit('4Gi')

    wait_task = wait_for_gemini_tuning(project_id=project_id, region=region, tuning_job_name=start_tuning_task.output, poll_interval_seconds=poll_interval_seconds)
    wait_task.set_caching_options(False)
    wait_task.set_cpu_limit('1')
    wait_task.set_memory_limit('4Gi')

compiler.Compiler().compile(gemini_tuning_pipeline, 'gemini_tuning_pipeline.json')
print('compiled restored full pipeline')
