from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID
import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy.orm import Session

from app.core.models import ConceptScore, StudentTopicCluster


def compute_clusters(class_id: str | UUID, chapter_id: str | UUID, db_session: Session):
    class_uuid = UUID(str(class_id))
    chapter_uuid = UUID(str(chapter_id))

    # Fetch all ConceptScore rows for this class + chapter
    scores = db_session.query(ConceptScore).filter(
        ConceptScore.class_id == class_uuid,
        ConceptScore.chapter_id == chapter_uuid
    ).all()

    # Group scores by student and keep the latest attempt
    student_latest_score = {}
    for s in scores:
        if s.overall_score is not None:
            student_id_str = str(s.student_id)
            if student_id_str not in student_latest_score or s.attempt_number > student_latest_score[student_id_str].attempt_number:
                student_latest_score[student_id_str] = s

    # If fewer than 3 students have scores, fallback to threshold-based bucketing
    if len(student_latest_score) < 3:
        clusters_data = {
            "struggling": [],
            "average": [],
            "strong": []
        }
        for sid_str, s in student_latest_score.items():
            if s.overall_score >= 7:
                clusters_data["strong"].append(sid_str)
            elif s.overall_score >= 4:
                clusters_data["average"].append(sid_str)
            else:
                clusters_data["struggling"].append(sid_str)
    else:
        student_ids = list(student_latest_score.keys())
        X = np.array([[student_latest_score[sid].overall_score] for sid in student_ids])

        # Run KMeans with 3 clusters
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)
        centroids = kmeans.cluster_centers_.flatten()

        # Map the cluster index to labels: lowest -> "struggling", middle -> "average", highest -> "strong"
        sorted_centroid_indices = np.argsort(centroids)
        label_mapping = {
            sorted_centroid_indices[0]: "struggling",
            sorted_centroid_indices[1]: "average",
            sorted_centroid_indices[2]: "strong"
        }

        clusters_data = {
            "struggling": [],
            "average": [],
            "strong": []
        }
        for student_idx, cluster_idx in enumerate(labels):
            sid = student_ids[student_idx]
            lbl = label_mapping[cluster_idx]
            clusters_data[lbl].append(sid)

    # Delete existing StudentTopicCluster rows for this class + chapter
    db_session.query(StudentTopicCluster).filter(
        StudentTopicCluster.class_id == class_uuid,
        StudentTopicCluster.chapter_id == chapter_uuid
    ).delete()
    db_session.commit()

    # Insert new cluster rows
    result_rows = []
    for label, sids in clusters_data.items():
        if sids:
            avg_score = sum(student_latest_score[sid].overall_score for sid in sids) / len(sids)
        else:
            avg_score = 0.0

        cluster_row = StudentTopicCluster(
            id=uuid.uuid4(),
            class_id=class_uuid,
            chapter_id=chapter_uuid,
            cluster_label=label,
            student_ids=sids,
            avg_score=float(avg_score),
            computed_at=datetime.now(timezone.utc)
        )
        db_session.add(cluster_row)
        result_rows.append(cluster_row)

    db_session.commit()
    return result_rows
