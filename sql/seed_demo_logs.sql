-- Demo seed for Grafana screenshots (Module 5-3).
-- Spreads realistic conversation_logs across the last hour so the latency
-- trend renders a line and the citations bar chart shows a ranking.
-- Idempotent: removes only prior *demo* rows (agent_answer starts with
-- '[demo seed]'), then re-centers timestamps. Never deletes live UI logs.

DELETE FROM conversation_logs
WHERE agent_answer LIKE '[demo seed]%';

INSERT INTO conversation_logs (created_at, user_question, agent_answer, latency_ms, used_citations) VALUES
  (NOW() - INTERVAL '57 min', 'What is the refund deadline after I receive the product?', '[demo seed] You can request a refund within 7 days of receiving your product.', 1180,
    '[{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb),
  (NOW() - INTERVAL '51 min', 'How can I get a refund?', '[demo seed] Click Request Refund in My Page, add a reason and photos; refunds complete within 3 business days.', 2210,
    '[{"id":"3._refund_process","section":"3. Refund Process"},{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb),
  (NOW() - INTERVAL '45 min', '환불 기한이 언제야?', '[demo seed] 상품 수령 후 7일 이내에 환불을 요청할 수 있습니다.', 1440,
    '[{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb),
  (NOW() - INTERVAL '39 min', 'Can I get a refund if I damaged the product myself?', '[demo seed] Refunds are not possible if the product is damaged due to customer negligence.', 1890,
    '[{"id":"2._non-refundable_conditions","section":"2. Non-Refundable Conditions"}]'::jsonb),
  (NOW() - INTERVAL '33 min', '¿Cuántos días tengo para pedir un reembolso?', '[demo seed] Puede solicitar un reembolso dentro de los 7 días posteriores a la recepción.', 1620,
    '[{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb),
  (NOW() - INTERVAL '27 min', 'When is customer support available?', '[demo seed] Support hours are weekdays 9:00 AM - 6:00 PM, excluding weekends and holidays.', 990,
    '[{"id":"4._contact_information","section":"4. Contact Information"}]'::jsonb),
  (NOW() - INTERVAL '21 min', 'Do I need to attach photos when requesting a refund?', '[demo seed] Yes, select the reason and attach relevant photos when requesting a refund.', 2040,
    '[{"id":"3._refund_process","section":"3. Refund Process"}]'::jsonb),
  (NOW() - INTERVAL '15 min', '전자기기를 전원 켠 후에도 환불이 되나요?', '[demo seed] 전자기기는 전원을 켠 이후에는 제품 결함이 아닌 한 환불이 어렵습니다.', 2560,
    '[{"id":"2._non-refundable_conditions","section":"2. Non-Refundable Conditions"}]'::jsonb),
  (NOW() - INTERVAL '9 min', 'How long does a refund take to complete?', '[demo seed] Once reviewed by Customer Service, refunds complete within 3 business days.', 1350,
    '[{"id":"3._refund_process","section":"3. Refund Process"},{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb),
  (NOW() - INTERVAL '3 min', 'How many days do I have to request a return after delivery?', '[demo seed] You have 7 days from delivery to request a return of an undamaged item.', 1120,
    '[{"id":"1._refund_period","section":"1. Refund Period"}]'::jsonb);
